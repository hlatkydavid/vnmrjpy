import sys
import os
import numpy as np
import nibabel as nib
import vnmrjpy as vj
import warnings
import matplotlib.pyplot as plt

class KspaceMaker():
    """Class to build the k-space from the raw fid data based on procpar.

    Raw fid_data is numpy.ndarray(blocks, traces * np) format. Should be
    untangled based on 'seqcon' or 'seqfil' parameters.
    seqcon chars refer to (echo, slice, Pe1, Pe2, Pe3)

    Should support compressed sensing
    In case of Compressed sensing the reduced kspace is filled with zeros
    to reach the intended final shape

    Leave rest of reconstruction to other classes/functions

    INPUT:  fid data = np.ndarra([blocks, np*traces])
            fid header
            procpar

    METHODS:
            make(): 
                return kspace = nump.ndarray\
                            ([rcvrs, phase, read, slice, echo*time])

    """
    def __init__(self, fid_data, fidheader, procpar, verbose=True):
        """Reads procpar"""

        def _get_arrayed_AP(p):
            """check for arrayed pars in procpar

            Return: dictionary {par : array_length}
            """

            AP_dict = {}
            for par in ['tr', 'te', 'fa']:
            
                pass

            return AP_dict

        self.p = vj.io.ProcparReader(procpar).read()
        self.fid_data = fid_data
        self.fid_header = fidheader
        self.rcvrs = str(self.p['rcvrs']).count('y')
        self.arrayed_AP = _get_arrayed_AP(self.p)
        apptype = self.p['apptype']
        self.config = vj.config
        self.verbose = verbose
        self.procpar = procpar
        # decoding skipint parameter
        # TODO
        # final kspace shape from config file
        self.dest_shape = (vj.config['rcvr_dim'],\
                            vj.config['pe_dim'],\
                            vj.config['ro_dim'],\
                            vj.config['slc_dim'],\
                            vj.config['et_dim'])
        self.pre_kspace = np.vectorize(complex)(fid_data[:,0::2],\
                                                fid_data[:,1::2])
        self.pre_kspace = np.array(self.pre_kspace,dtype='complex64')
 
        if verbose:
            print('Making k-space for '+ str(apptype)+' '+str(self.p['seqfil'])+\
                ' seqcon: '+str(self.p['seqcon']))

    def print_fid_header(self):
        for item in self.fhdr.keys():
            print(str('{} : {}').format(item, self.fhdr[item]))

    def make(self):
        """Build k-space from fid data

        Return: 
            kspace=numpy.ndarray([rcvrs,phase,readout,slice,echo/time])
        """
        def make_im2D():
            """Child method of 'make', provides the same as vnmrj im2Drecon"""
            kspace = self.pre_kspace
            p = self.p
            (read, phase, slices) = (int(p['np'])//2, \
                                            int(p['nv']), \
                                            int(p['ns']))
            shiftaxis = (self.config['pe_dim'],self.config['ro_dim'])
            if 'ne' in p.keys():
                echo = int(p['ne'])
            else:
                echo = 1

            time = 1

            if p['seqcon'] == 'nccnn':
                shape = (self.rcvrs, phase, slices, echo*time, read)
                kspace = np.reshape(kspace, shape, order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)


            elif p['seqcon'] == 'nscnn':

                raise(Exception('not implemented'))

            elif p['seqcon'] == 'ncsnn':

                preshape = (self.rcvrs, phase, slices*echo*time*read)
                shape = (self.rcvrs, phase, slices, echo*time, read)
                kspace = np.reshape(kspace, preshape, order='F')
                kspace = np.reshape(kspace, shape, order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)

            elif p['seqcon'] == 'ccsnn':

                preshape = (self.rcvrs, phase, slices*echo*time*read)
                shape = (self.rcvrs, phase, slices, echo*time, read)
                kspace = np.reshape(kspace, preshape, order='F')
                kspace = np.reshape(kspace, shape, order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)

            if int(p['sliceorder']) == 1: # 1 if interleaved slices
                c = np.zeros(kspace.shape, dtype=complex)
                c[...,1::2,:] = kspace[...,slices//2:,:]
                c[...,0::2,:] = kspace[...,:slices//2,:]
                kspace = c

            return kspace

        def make_im2Dcs():
            """
            These (*cs) are compressed sensing variants
            """

            def decode_skipint_2D(skipint):

               pass
 
            raise(Exception('not implemented'))
        def make_im2Depi():
            raise(Exception('not implemented'))
        def make_im2Depics():
            raise(Exception('not implemented'))
        def make_im2Dfse():
            warnings.warn('not working correctly')
            kspace = self.pre_kspace
            
            p = self.p
            petab = vj.util.getpetab(self.procpar,is_procpar=True)
            print(petab)
            nseg = int(p['nseg'])  # seqgments
            etl = int(p['etl'])  # echo train length
            kzero = int(p['kzero'])  
            images = int(p['images'])  # repetitions
            (read, phase, slices) = (int(p['np'])//2, \
                                            int(p['nv']), \
                                            int(p['ns']))
            shiftaxis = (self.config['pe_dim'],self.config['ro_dim'])

            echo = 1
            time = images

            if p['seqcon'] == 'nccnn':

                preshape = (self.rcvrs, phase//etl, slices, echo*time, etl, read)
                preshape2 = (self.rcvrs, slices, phase,echo*time, read )
                #prepreshape = (self.rcvrs, etl*read, phase*slices*echo*time//etl)
                #preshape = (self.rcvrs, echo*time*slices, phase//etl, read*etl)
                shape = (self.rcvrs, echo*time, slices, phase, read)
                #kspace = np.reshape(kspace, prepreshape, order='F')
                #kspace = np.reshape(kspace, preshape, order='F')
                kspace = np.reshape(kspace, preshape, order='C')
                plt.subplot(1,4,1)
                plt.imshow(np.absolute(kspace[1,:,4,0,0,:]))
                plt.subplot(1,4,2)
                plt.imshow(np.absolute(kspace[1,:,4,0,1,:]))
                plt.subplot(1,4,3)
                plt.imshow(np.absolute(kspace[1,:,4,0,2,:]))
                kspace = np.swapaxes(kspace,1,3)
                kspace = np.reshape(kspace, shape, order='C')
                kspace = np.swapaxes(kspace,1,3)
                plt.subplot(1,4,4)
                plt.imshow(np.absolute(kspace[1,:,4,0,:]))
                plt.show()
                kspace = np.reshape(kspace, shape, order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)
            else:
                raise(Exception('not implemented'))
            
            return kspace

        def make_im2Dfsecs():
            raise(Exception('not implemented'))
        def make_im3D():

            kspace = self.pre_kspace
            p = self.p
            (read, phase, phase2) = (int(p['np'])//2, \
                                    int(p['nv']), \
                                     int(p['nv2']))

            shiftaxis = (self.config['pe_dim'],\
                        self.config['ro_dim'],\
                        self.config['pe2_dim'])

            if 'ne' in p.keys():
                echo = int(p['ne'])
            else:
                echo = 1

            time = 1

            if p['seqcon'] == 'nccsn':
            
                preshape = (self.rcvrs,phase2,phase*echo*time*read)
                shape = (self.rcvrs,phase,phase2,echo*time,read)
                kspace = np.reshape(kspace,preshape,order='F')
                kspace = np.reshape(kspace,shape,order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)

            if p['seqcon'] == 'ncccn':
                #TODO fix 
                preshape = (self.rcvrs,phase2,phase*echo*time*read)
                shape = (self.rcvrs,phase,phase2,echo*time,read)
                kspace = np.reshape(kspace,preshape,order='F')
                kspace = np.reshape(kspace,shape,order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)
    
            if p['seqcon'] == 'cccsn':
            
                preshape = (self.rcvrs,phase2,phase*echo*time*read)
                shape = (self.rcvrs,phase,phase2,echo*time,read)
                kspace = np.reshape(kspace,preshape,order='F')
                kspace = np.reshape(kspace,shape,order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)

            if p['seqcon'] == 'ccccn':
                
                #preshape = (self.rcvrs,phase*phase2*echo*time*read)
                shape = (self.rcvrs,phase2,phase,echo*time,read)
                #kspace = np.reshape(kspace,preshape,order='F')
                kspace = np.reshape(kspace,shape,order='C')
                kspace = np.moveaxis(kspace, [0,4,1,2,3], self.dest_shape)

            return kspace

        def make_im3Dcs():
            """
            3D compressed sensing
            sequences : ge3d, mge3d, se3d, etc
            """
            # -------------------im3Dcs Make helper functions ---------------------

            def decode_skipint_3D(skipint):
                """
                Takes 'skipint' parameter and returns a 0-1 matrix according to it
                which tells what lines are acquired in the phase1-phase2 plane
                """
                BITS = 32  # Skipint parameter is 32 bit encoded binary, see spinsights
                skip_matrix = np.zeros([int(p['nv']), int(p['nv2'])])
                skipint = [int(x) for x in skipint]
                skipint_bin_vals = [str(np.binary_repr(d, BITS)) for d in skipint]
                skipint_bin_vals = ''.join(skipint_bin_vals)
                skipint_bin_array = np.asarray([int(i) for i in skipint_bin_vals])
                skip_matrix = np.reshape(skipint_bin_array, skip_matrix.shape)

                return skip_matrix

            def fill_kspace_3D(pre_kspace, skip_matrix, shape):
                """
                Fills up reduced kspace with zeros according to skip_matrix
                returns zerofilled kspace in the final shape
                """
                kspace = np.zeros(shape, dtype=complex)
                if self.p['seqcon'] == 'ncccn':

                    n = int(self.p['nv'])
                    count = 0
                    for i in range(skip_matrix.shape[0]):
                        for k in range(skip_matrix.shape[1]):
                            if skip_matrix[i,k] == 1:
                                kspace[:,i,k,:,:] = pre_kspace[:,count,:,:]
                                count = count+1
                return kspace

            #------------------------im3Dcs make start -------------------------------

            kspace = self.pre_kspace
            p = self.p
            (read, phase, phase2) = (int(p['np'])//2, \
                                    int(p['nv']), \
                                     int(p['nv2']))

            shiftaxis = (self.config['pe_dim'],\
                        self.config['ro_dim'],\
                        self.config['pe2_dim'])

            if 'ne' in p.keys():
                echo = int(p['ne'])
            else:
                echo = 1

            time = 1

            if p['seqcon'] == 'nccsn':

                pass

            if p['seqcon'] == 'ncccn':
            
                skip_matrix = decode_skipint_3D(p['skipint'])
                pre_phase = int(self.fid_header['ntraces'])    
                shape = (self.rcvrs, phase, phase2, echo*time, read)
                pre_shape = (self.rcvrs, pre_phase, echo*time, read)
                pre_kspace = np.reshape(kspace, pre_shape, order='c')
                kspace = fill_kspace_3D(pre_kspace, skip_matrix, shape)
                kspace = np.moveaxis(kspace, [0,4,1,2,3],[0,1,2,3,4])
                
            return kspace

        def make_im3Dute():
            raise(Exception('not implemented')) 
        # ----------------Handle sequence exceptions first---------------------

        if self.verbose == True:
            print('KspaceMaker: making seqfil : {}'.format(self.p['seqfil']))


        if str(self.p['seqfil']) == 'ge3d_elliptical':
           
            return make_im3Dcs()

        #--------------------------Handle by apptype---------------------------

        if self.p['apptype'] == 'im2D':

            return make_im2D()

        elif self.p['apptype'] == 'im2Dcs':

            return make_im2Dcs()

        elif self.p['apptype'] == 'im2Depi':

            return make_im2Depi()

        elif self.p['apptype'] == 'im2Depics':

            return make_im2Depics()

        elif self.p['apptype'] == 'im2Dfse':

            return make_im2Dfse()

        elif self.p['apptype'] == 'im2Dfsecs':

            return make_im2Dfsecs()

        elif self.p['apptype'] == 'im3D':

            return make_im3D()

        elif self.p['apptype'] == 'im3Dcs':

            return make_im3Dcs()

        elif self.p['apptype'] == 'im3Dute':

            return make_im3Dute()

        else:
            raise(Exception('Could not find apptype. Maybe not implemented?'))

