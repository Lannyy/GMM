import numpy as np
import cv2 as cv
import os

init_sigma = 225 * np.eye(3)  # 初始协方差矩阵
init_u = None
init_alpha = 0.01
epsilon = 0.00000001  # 防止除0，为了数值稳定性


class Gaussian():
    def __init__(self, u, sigma):
        self.u = u
        self.sigma = sigma


class GaussianMat():
    def __init__(self, shape, k):
        self.shape = shape
        self.k = k
        g = [Gaussian(init_u, init_sigma) for i in range(k)]  # 初始化高斯分布，均值为0-255随机，标准差为6
        self.mat = [[[Gaussian(init_u, init_sigma) for i in range(k)] for j in range(shape[1])] for l in
                    range(shape[0])]  # 将每个像素点建模成多维的混合高斯分布
        # 对权重进行初始化，初始情况下最好是[1,0,0,0]，为了数值稳定性选择为[0.7,0.1,0.1,0.1]
        self.weight = [[[0.7, 0.1, 0.1, 0.1] for j in range(shape[1])] for l in range(shape[0])]


class GMM():
    def __init__(self, data_dir, train_num, alpha=init_alpha):
        self.data_dir = data_dir
        self.train_num = train_num
        self.alpha = alpha
        self.g_mat = None
        self.K = None

    def check(self, pixel, gaussian):
        u = np.mat(gaussian.u).T
        x = np.mat(np.reshape(pixel, (3, 1)))
        sigma = np.mat(gaussian.sigma)
        d = np.sqrt((x - u).T * sigma.I * (x - u))
        if d < 2.5:
            return True
        else:
            return False

    def train(self, K=4):
        self.K = K
        file_list = []
        for i in range(self.train_num):
            file_name = os.path.join(self.data_dir, 'b%05d' % i + '.bmp')
            file_list.append(file_name)
        img_init = cv.imread(file_list[0])
        img_shape = img_init.shape

        self.g_mat = GaussianMat(img_shape, K)
        for i in range(img_shape[0]):
            for j in range(img_shape[1]):
                for k in range(self.K):
                    self.g_mat.mat[i][j][k].u = np.array(img_init[i][j]).reshape(1, 3)
        # for i in range(4):
        #     print('u:{}'.format(self.g_mat.mat[10][10][i].u))
        for file in file_list:  # 更新的过程
            print('processing:{}'.format(file))
            img = cv.imread(file)
            for i in range(img.shape[0]):
                for j in range(img.shape[1]):
                    flag = 0  # 一个flag检测是否有一个高斯与之匹配
                    for k in range(K):
                        if self.check(img[i][j], self.g_mat.mat[i][j][k]):
                            flag = 1
                            m = 1
                            self.g_mat.weight[i][j][k] = self.g_mat.weight[i][j][k] + self.alpha * (
                                m - self.g_mat.weight[i][j][k]) # 如果与第k个高斯匹配，那么增大其权重
                            u, sigma, x = self.g_mat.mat[i][j][k].u, self.g_mat.mat[i][j][k].sigma, img[i][j].astype(
                                np.float)
                            delta = x - u
                            self.g_mat.mat[i][j][k].u = u + m * (# 如果与第k个高斯匹配，改变该高斯分布的均值使其接近x
                                self.alpha / (self.g_mat.weight[i][j][k] + epsilon)) * delta
                            self.g_mat.mat[i][j][k].sigma = sigma + m * (   # 这个公式忘了啥意思
                                self.alpha / (self.g_mat.weight[i][j][k] + epsilon)) * (
                                                                        np.matmul(delta, delta.T) - sigma)
                        else:
                            m = 0
                            self.g_mat.weight[i][j][k] = self.g_mat.weight[i][j][k] + self.alpha * (
                                m - self.g_mat.weight[i][j][k])
                    if flag == 0:  # 如果没有匹配的则重新初始化
                        w_list = [self.g_mat.weight[i][j][k] for k in range(K)]
                        id = w_list.index(min(w_list))
                        self.g_mat.mat[i][j][id].u = np.array(img[i][j]).reshape(1, 3)
                        self.g_mat.mat[i][j][id].sigma = np.array(init_sigma)
                    # 对权值进行归一化
                    s = sum([self.g_mat.weight[i][j][temp] for temp in range(K)])
                    for temp in range(K):
                        self.g_mat.weight[i][j][temp] /= s
            print('img:{}'.format(img[10][10]))
            print('weight:{}'.format(self.g_mat.weight[10][10]))
            for i in range(4):
                print('u:{}'.format(self.g_mat.mat[10][10][i].u))

    def infer(self, img):  # 推断图片的背景，如果像素为背景则rgb都设为255，如果不是背景则不进行处理
        result = np.array(img)
        # print('img:{}'.format(img[10][10]))
        # print('weight:{}'.format(self.g_mat.weight[10][10]))
        # for i in range(4):
        #     print('u:{}'.format(self.g_mat.mat[10][10][i].u))
        #     print('sigma:{}'.format(self.g_mat.mat[10][10][i].sigma))
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                gaussian_pixel = self.g_mat.mat[i][j]
                # if i % 100 == 0 and j % 100 == 0:
                #     print(self.g_mat.weight[i][j])
                for g in range(4):
                    if self.check(img[i][j], gaussian_pixel[g]) and self.g_mat.weight[i][j][
                        g] > 0.25:  # 阈值，将符合任意一个权重较大的高斯分布的像素点变为白色，即为背景
                        result[i][j] = [255, 255, 255]
                        continue
        return result
