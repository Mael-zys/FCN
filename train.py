from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
#import visdom
import cv2
from BagData import test_dataloader, train_dataloader
from FCN import FCN8s, FCN16s, FCN32s, FCNs, VGGNet
import os

# 绘制loss变化图，包含了train loss和test loss
def draw_loss_plot(train_loss_list=[], test_loss_list=[]):
    x1 = range(0, len(train_loss_list))
    x2 = range(0, len(test_loss_list))
    y1 = train_loss_list
    y2 = test_loss_list
    plt.switch_backend('agg')
    plt.subplot(2, 1, 1)
    plt.plot(x1, y1, 'o-')
    plt.title('train loss vs. iterators')
    plt.ylabel('train loss')
    plt.subplot(2, 1, 2)
    plt.plot(x2, y2, '.-')
    plt.xlabel('test loss vs. iterators')
    plt.ylabel('test loss')
    plt.savefig("train_loss.png")

model_path='model_test/0.01best.model'

def train(epo_num=50, show_vgg_params=False):

    #vis = visdom.Visdom()
    os.environ["CUDA_VISIBLE_DEVICES"] = '3'
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(device)
    vgg_model = VGGNet(requires_grad=True, show_params=show_vgg_params)
    fcn_model = FCNs(pretrained_net=vgg_model, n_class=2)
    if not torch.cuda.is_available():
        fcn_model.load_state_dict(torch.load(model_path, map_location='cpu'))
    else:
        fcn_model.load_state_dict(torch.load(model_path))
    fcn_model = fcn_model.to(device)
    criterion = nn.BCELoss().to(device)
    # criterion = nn.BCEWithLogitsLoss().to(device)
    optimizer = optim.SGD(fcn_model.parameters(), lr=1e-3, momentum=0.7)
    # scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=6, gamma=0.1)
    all_train_iter_loss = []
    all_test_iter_loss = []

    # start timing
    prev_time = datetime.now()
    for epo in range(epo_num):
        
        train_loss = 0
        fcn_model.train()
        for index, (bag, bag_msk) in enumerate(train_dataloader):
            # bag.shape is torch.Size([4, 3, 160, 160])
            # bag_msk.shape is torch.Size([4, 2, 160, 160])

            bag = bag.to(device)
            bag_msk = bag_msk.to(device)

            optimizer.zero_grad()
            output = fcn_model(bag)
            output = torch.sigmoid(output) # output.shape is torch.Size([4, 2, 160, 160])
            loss = criterion(output, bag_msk)
            loss.backward()
            iter_loss = loss.item()
            all_train_iter_loss.append(iter_loss)
            train_loss += iter_loss
            optimizer.step()

            output_np = output.cpu().detach().numpy().copy() # output_np.shape = (4, 2, 160, 160)  
            output_np = np.argmin(output_np, axis=1)
            #print("size of output is {}".format(output_np.shape))
            bag_msk_np = bag_msk.cpu().detach().numpy().copy() # bag_msk_np.shape = (4, 2, 160, 160) 
            bag_msk_np = np.argmin(bag_msk_np, axis=1)

            if np.mod(index, 50) == 0:
                print('epoch {}, {}/{},train loss is {}'.format(epo, index, len(train_dataloader), iter_loss))
                # vis.close()
                # vis.images(output_np[:, None, :, :], win='train_pred', opts=dict(title='train prediction')) 
                # vis.images(bag_msk_np[:, None, :, :], win='train_label', opts=dict(title='label'))
                # vis.line(all_train_iter_loss, win='train_iter_loss',opts=dict(title='train iter loss'))

                # plt.subplot(1, 2, 1) 
                # plt.imshow(np.squeeze(bag_msk_np[0, ...]), 'gray')
                # plt.subplot(1, 2, 2) 
                # plt.imshow(np.squeeze(output_np[0, ...]), 'gray')
                # plt.pause(0.5)
                # plt.savefig("Result/"+str(index)+"_train.png")
                cv2.imwrite("Result/"+str(index)+"_train.jpg",255*np.squeeze(output_np[0, ...]))

        
        test_loss = 0
        fcn_model.eval()
        num_test=0
        with torch.no_grad():
            for index, (bag, bag_msk) in enumerate(test_dataloader):

                bag = bag.to(device)
                bag_msk = bag_msk.to(device)

                optimizer.zero_grad()
                output = fcn_model(bag)
                output = torch.sigmoid(output) # output.shape is torch.Size([4, 2, 160, 160])
                loss = criterion(output, bag_msk)
                iter_loss = loss.item()
                
                test_loss += iter_loss
                num_test = index +1
                output_np = output.cpu().detach().numpy().copy() # output_np.shape = (4, 2, 160, 160)  
                output_np = np.argmin(output_np, axis=1)
                bag_msk_np = bag_msk.cpu().detach().numpy().copy() # bag_msk_np.shape = (4, 2, 160, 160) 
                bag_msk_np = np.argmin(bag_msk_np, axis=1)
        
                if np.mod(index, 10) == 0:
                    # plt.subplot(1, 2, 1) 
                    # plt.imshow(np.squeeze(bag_msk_np[0, ...]), 'gray')
                    # plt.subplot(1, 2, 2) 
                    # plt.imshow(np.squeeze(output_np[0, ...]), 'gray')
                    # plt.pause(0.5)
                    # plt.savefig("Result/"+str(index)+"_test.png")
                    cv2.imwrite("Result/"+str(index)+"_test.jpg",255*np.squeeze(output_np[0, ...]))
        all_test_iter_loss.append(test_loss/num_test)

        cur_time = datetime.now()
        h, remainder = divmod((cur_time - prev_time).seconds, 3600)
        m, s = divmod(remainder, 60)
        time_str = "Time %02d:%02d:%02d" % (h, m, s)
        prev_time = cur_time

        print('epoch train loss = %f, epoch test loss = %f, %s'
                %(train_loss/len(train_dataloader), test_loss/len(test_dataloader), time_str))
        
        draw_loss_plot(all_train_iter_loss,all_test_iter_loss)

        # if np.mod(epo+1, 10) == 0:
            #torch.save(fcn_model, 'checkpoints/fcn_model_{}.pt'.format(epo+1))
        torch.save(fcn_model.state_dict(), 'model_test/fcn_0.001_{0}.model'.format(epo))
        #torch.save(fcn_model, 'model/fcn_{0}.model'.format(epo+1))
        print('saveing model/fcn_{0}.model'.format(epo))
        # scheduler.step()


if __name__ == "__main__":

    train(epo_num=50, show_vgg_params=False)
