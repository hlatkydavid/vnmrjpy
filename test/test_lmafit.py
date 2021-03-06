import vnmrjpy as vj
import numpy as np
import imageio
import unittest

class Test_Lmafit(unittest.TestCase):

    def test_solve_boat(self):

        img = imageio.imread(vj.pics+'/boat.png')
        mask = np.random.rand(img.shape[0],img.shape[1])
        mask[mask >= 0.7] = 1
        mask[mask < 0.7] = 0
        img_masked = np.multiply(img,mask)

        mse_start = np.abs(((img_masked - img)**2).mean(axis=None))
        self.assertEqual(len(img.shape),2)

        lmafit = vj.aloha.Lmafit(img_masked,\
                    realtimeplot=False,\
                    verbose=False,\
                    tol=5e-3)
        X,Y,out = lmafit.solve()
        img_filled = X.dot(Y)
        mse_end = np.abs(((img_filled - img)**2).mean(axis=None))
        self.assertTrue(mse_end < mse_start)
        print('Starting, ending  MSE : {}, {}'.format(mse_start,mse_end))


