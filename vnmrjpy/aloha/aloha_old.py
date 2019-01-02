
import sys
import numpy as np
import numba
import glob
import nibabel as nib
import matplotlib.pyplot as plt
import timeit
import time
import copy

# TESTING PARAMETERS

TESTDIR_ROOT = '/home/david/dev/vnmrjpy/dataset/cs/'
#TESTDIR = TESTDIR_ROOT + 'ge3d_angio_HD_s_2018072604_HD_01.cs'
#TESTDIR = TESTDIR_ROOT + 'gems_s_2018111301_axial_0_0_0_01.cs'
TESTDIR = TESTDIR_ROOT+'mems_s_2018111301_axial_0_0_0_01.cs'
PROCPAR = TESTDIR+'/procpar'
# undersampling dimension
CS_DIM = (1,4)  # phase and slice
RO_DIM = 2
STAGES = 3
FILTER_SIZE = (7,5)

SOLVER = 'ADMM'
# different tolerance for the tages
LMAFIT_TOL_LIST = [5e-2,5e-3,5e-4]
"""
NOTE: testing angio data: rcvrs, phase1, phase2, read
NOTE gems data: 
"""
class ALOHA():
    """
    Class for compressed sensing completion using ALOHA:

    ref: Jin et al.: A general framework for compresed sensing and parallel
        MRI using annihilation filter based low-rank matrix completion (2016)
    
    Process:

        1. kspace weighing
        2. pyramidal decomposition in case of wavelet transform
        3. Hankel matrix formation, RANK ESTIMATION (MAYBE)
        4. matrix completion (Multiple approaches maybe)
        5. kspace unweighing
    """
    def __init__(self, procpar, kspace_cs, kspace_orig, reconpar=None):
        """
        INPUT:
            procpar : path to procpar file
            kspace_cs : zerofilled cs kspace in numpy array
            reconpar: dictionary, ALOHA recon parameters
                    keys:
                        filter_size
                        rcvrs
                        cs_dim
                        recontype
        """
        def get_recontype(reconpar):

            if 'angio' in self.p['pslabel']:
                recontype = 'kx-ky_angio'
            elif 'mems' in self.p['pslabel']:
                recontype = 'k-t'
            return recontype

        def get_reconpar():

            pass

        self.p = procparReader(procpar).read() 
        recontype = get_recontype(reconpar)
        rcvrs = self.p['rcvrs'].count('y')

        self.rp = {'filter_size' : FILTER_SIZE ,\
                    'cs_dim' : CS_DIM ,\
                    'ro_dim' : RO_DIM, \
                    'rcvrs' : rcvrs , \
                    'recontype' : recontype,\
                    'timedim' : 4,\
                    'stages' : STAGES,\
                    'virtualcoilboost' : False,\
                    'solver' : 'lmafit'}
        self.kspace_cs = np.array(kspace_cs, dtype='complex64')
        #TODO kspace orig is only for testing here
        self.kspace = np.array(kspace_orig, dtype='complex64')

    def recon(self):
        """
        """
        #----------------------------INIT---------------------------------
        def virtualcoilboost_(data):
            pass 
            return boosted

        if self.rp['virtualcoilboost'] == False:
            kspace_completed = copy.deepcopy(self.kspace_cs)
        elif self.rp['virtualcoilboost'] == True:
            self.kspace_cs = virtualcoilboost_(self.kspace_cs)
            kspace_completed = copy.deepcopy(self.kspace_cs)

        #------------------------------------------------------------------
        #           2D :    k-t ; kx-ky ; kx-ky_angio
        #------------------------------------------------------------------
        if self.rp['recontype'] in ['k-t','kx-ky','kx-ky_angio']:


            if self.rp['recontype'] == 'k-t':
            #----------------------MAIN INIT----------------------------    
                slice3d_shape = (self.kspace_cs.shape[0],\
                                self.kspace_cs.shape[1],\
                                self.kspace_cs.shape[4])

                x_len = kspace_cs.shape[self.rp['cs_dim'][0]]
                t_len = kspace_cs.shape[self.rp['cs_dim'][1]]
                #each element of weight list is an array of weights in stage s
                weights_list = make_pyramidal_weights_kxt(x_len, t_len, self.rp)
                factors = make_hankel_decompose_factors(slice3d_shape, self.rp)
            
            #print('factors len : {}'.format(len(factors)))
            #print('factors[0] shape : {}'.format(factors[0][0].shape))
           
            #------------------MAIN ITERATION----------------------------    
            for slc in range(self.kspace_cs.shape[3]):

                for x in range(self.kspace_cs.shape[self.rp['cs_dim'][0]]):
                    #TODO plotind is for testing only delete afterward
                    if x == self.kspace_cs.shape[self.rp['cs_dim'][0]]//2-5:
                        plotind = 1
                    else: 
                        plotind = 0

                    slice3d = self.kspace_cs[:,:,x,slc,:]
                    slice3d_orig = copy.deepcopy(slice3d)
                    slice3d_completed = pyramidal_solve_kt(slice3d,\
                                                        slice3d_orig,\
                                                        slice3d_shape,\
                                                        weights_list,\
                                                        factors,\
                                                        self.rp)
                    kspace_completed[:,:,x,slc,:] = slice3d_completed
            
                    print('slice {}/{} line {}/{} done.'.format(\
                                slc+1,kspace_cs.shape[3],x+1,kspace_cs.shape[2]))

            return kspace_completed

#----------------------------------FOR TESTING---------------------------------

def save_test_data(kspace_orig, kspace_cs, kspace_filled, affine):

    def makeimg(kspace):

        img_space = np.fft.ifft2(kspace, axes=(1,2), norm='ortho')
        img_space = np.fft.fftshift(img_space, axes=(1,2))
        return img_space

    SAVEDIR = '/home/david/dev/vnmrjpy/aloha/result_aloha/'

    # saving kspace
    kspace_orig_ch1 = nib.Nifti1Image(np.absolute(kspace_orig[0,...]), affine) 
    nib.save(kspace_orig_ch1, SAVEDIR+'kspace_orig')
    kspace_cs_ch1 = nib.Nifti1Image(np.absolute(kspace_cs[0,...]), affine) 
    nib.save(kspace_cs_ch1, SAVEDIR+'kspace_cs')
    kspace_filled_ch1 = nib.Nifti1Image(np.absolute(kspace_filled[0,...]),\
                                         affine) 
    nib.save(kspace_filled_ch1, SAVEDIR+'kspace_filled')
    # saving 6D raw kspace - 5D standard, 6th real/imag
    kspace_filled_6d_data = np.stack((np.real(kspace_filled), \
                            np.imag(kspace_filled)), \
                            axis=len(kspace_filled.shape))
    kspace_filled_6d = nib.Nifti1Image(kspace_filled_6d_data,affine)
    nib.save(kspace_filled_6d, SAVEDIR+'kspace_filled_6d')
    
    


    imgspace_orig = makeimg(kspace_orig) 
    imgspace_cs = makeimg(kspace_cs) 
    imgspace_filled = makeimg(kspace_filled) 
    # saving combined magnitude
    name_list = ['img_orig_full','img_cs_full','img_filled_full']
    for num,item in enumerate([imgspace_orig,imgspace_cs,imgspace_filled]):
        img_comb = np.mean(np.absolute(item),axis=0)
        img_comb = nib.Nifti1Image(img_comb,affine)
        nib.save(img_comb,SAVEDIR+name_list[num])
    # saving for fslview
    imgspace_orig_ch1 = nib.Nifti1Image(np.absolute(imgspace_orig[0,...]),\
                                        affine) 
    nib.save(imgspace_orig_ch1, SAVEDIR+'imgspace_orig')
    imgspace_cs_ch1 = nib.Nifti1Image(np.absolute(imgspace_cs[0,...]),\
                                        affine) 
    nib.save(imgspace_cs_ch1, SAVEDIR+'imgspace_cs')
    imgspace_filled_ch1 = nib.Nifti1Image(np.absolute(imgspace_filled[0,...]),\
                                        affine) 
    nib.save(imgspace_filled_ch1, SAVEDIR+'imgspace_filled')

    #saving 5d magnitude and phase
    imgspace_filled_5d_magn = np.absolute(imgspace_filled)
    imgspace_filled_5d_phase = np.arctan2(np.imag(imgspace_filled),\
                                        np.real(imgspace_filled))
    magn5d = nib.Nifti1Image(imgspace_filled_5d_magn,affine)
    phase5d = nib.Nifti1Image(imgspace_filled_5d_phase,affine)
    nib.save(magn5d,SAVEDIR+'img_filled_5d_magn')
    nib.save(phase5d,SAVEDIR+'img_filled_5d_phase')

def load_test_data():

    slc = 10
    slcnum = 1

    imag = []
    real = []
    imag_orig = []
    real_orig = []

    mask_img = nib.load(TESTDIR+'/kspace_mask.nii.gz')
    affine = mask_img.affine
    mask = mask_img.get_fdata()

    for item in sorted(glob.glob(TESTDIR+'/kspace_imag*')):
        data = nib.load(item).get_fdata()
        imag_orig.append(data)
        data = np.multiply(data, mask)
        imag.append(data)

    for item in sorted(glob.glob(TESTDIR+'/kspace_real*')):
        data = nib.load(item).get_fdata()
        real_orig.append(data)
        data = np.multiply(data, mask)
        real.append(data)

    imag = np.asarray(imag)
    real = np.asarray(real)
    imag_orig = np.asarray(imag_orig)
    real_orig = np.asarray(real_orig)
    kspace_cs = np.vectorize(complex)(real, imag)
    kspace_orig = np.vectorize(complex)(real_orig, imag_orig)
    print('kspace shape : {}'.format(kspace_cs.shape))
    print('mask shape : {}'.format(mask.shape))
    #plt.imshow(np.real(kspace_cs[0,:,:,10,4]), cmap='gray')
    #plt.show()
    print('affine shape : {}'.format(affine.shape))
    return (kspace_orig[:,:,:,slc:slc+slcnum,:],\
            kspace_cs[:,:,:,slc:slc+slcnum,:],\
             affine)

def load_test_kydata():

    # preferably mge3d
    TESTDIRXY = TESTDIR_ROOT 
    slc = 10
    slcnum = 5

    imag = []
    real = []
    imag_orig = []
    real_orig = []

    mask_img = nib.load(TESTDIRXY+'/kspace_mask.nii.gz')
    affine = mask_img.affine
    mask = mask_img.get_fdata()

    for item in sorted(glob.glob(TESTDIRXY+'/kspace_imag*')):
        data = nib.load(item).get_fdata()
        imag_orig.append(data)
        data = np.multiply(data, mask)
        imag.append(data)

    for item in sorted(glob.glob(TESTDIRXY+'/kspace_real*')):
        data = nib.load(item).get_fdata()
        real_orig.append(data)
        data = np.multiply(data, mask)
        real.append(data)

    imag = np.asarray(imag)
    real = np.asarray(real)
    imag_orig = np.asarray(imag_orig)
    real_orig = np.asarray(real_orig)
    kspace_cs = np.vectorize(complex)(real, imag)
    kspace_orig = np.vectorize(complex)(real_orig, imag_orig)
    print('kspace shape : {}'.format(kspace_cs.shape))
    print('mask shape : {}'.format(mask.shape))
    #plt.imshow(np.real(kspace_cs[0,:,:,10,4]), cmap='gray')
    #plt.show()
    print('affine shape : {}'.format(affine.shape))
    return (kspace_orig[:,:,:,slc:slc+slcnum,:],\
            kspace_cs[:,:,:,slc:slc+slcnum,:],\
             affine)
if __name__ == '__main__':

    kspace_orig, kspace_cs, affine = load_test_data()

    aloha = ALOHA(PROCPAR, kspace_cs, kspace_orig)
    start_time = time.time()
    kspace_filled = aloha.recon()
    print('elapsed time {}'.format(time.time()-start_time))

    save_test_data(kspace_orig, kspace_cs, kspace_filled, affine)
