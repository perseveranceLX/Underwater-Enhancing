import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F

def conv2d_bn(in_channels, out_channels, kernel_size, stride=1, padding=None, groups=1, bias=False, activation=nn.ReLU(inplace=True)):
    if padding is None:
            if stride == 1:
                padding = (kernel_size-1)//2
            else:
                padding = 0
    block = [nn.Conv2d(in_channels, out_channels, kernel_size, stride=1, padding=padding, groups=1, bias=False),
             nn.BatchNorm2d(out_channels)]
    if activation is not None:
        block.append(activation)
    return nn.Sequential(*block)

class Decompose(nn.Module):

    def __init__(self, 
                 num_layers, 
                 channel=64, 
                 kernel_size=3):
        super(Decompose, self).__init__()
        self.num_layers = num_layers
        self.channel = channel
        self.kernel_size = kernel_size

        self.conv1 = conv2d_bn(in_channels=4, out_channels=self.channel, kernel_size=self.kernel_size)
        self.conv_block = self._make_layers(self.channel, kernel_size=self.kernel_size, padding=None, num_of_layers=self.num_layers)
        self.conv2 = conv2d_bn(in_channels=self.channel, out_channels=4, kernel_size=self.kernel_size, activation=None)
    
    def _make_layers(self, num_chnl, kernel_size, padding, num_of_layers, groups=1):
        layers = []
        for _ in range(num_of_layers):
            layers.append(conv2d_bn(in_channels=num_chnl, out_channels=num_chnl, kernel_size=kernel_size, padding=padding, groups=groups))
        return nn.Sequential(*layers)

    def forward(self, x):
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        x_max, _ = torch.max(x, dim=1)
        x = torch.cat([x, x_max.unsqueeze(1)], dim=1)
        x = self.conv1(x)
        x = self.conv_block(x)
        x = self.conv2(x)
        R = torch.sigmoid(x[:, 0:3, :, :].contiguous())
        I = torch.sigmoid(x[:, 3:, :, :].contiguous())
        return R, I

def deocmp_loss(input_high, input_low, R_high, I_high, R_low, I_low):
    recon_loss_low = torch.mean(torch.abs(R_low * I_low.repeat(1, 3, 1, 1) - input_low))
    recon_loss_high = torch.mean(torch.abs(R_high * I_high.repeat(1, 3, 1, 1) - input_high))
    recon_loss_mutal_low = torch.mean(torch.abs(R_high * I_low.repeat(1, 3, 1, 1) - input_low))
    recon_loss_mutal_high = torch.mean(torch.abs(R_low * I_high.repeat(1, 3, 1, 1) - input_high))
    equal_R_loss = torch.mean(torch.abs(R_high - R_low))
    # self.Ismooth_loss_low = self.smooth(I_low, R_low)
    # self.Ismooth_loss_high = self.smooth(I_high, R_high)
    loss_Decom = recon_loss_low + recon_loss_high + 0.001 * recon_loss_mutal_low \
                 + 0.001 * recon_loss_mutal_high + 0.01 * equal_R_loss
    return loss_Decom
        





