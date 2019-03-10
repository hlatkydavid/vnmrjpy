import vnmrjpy as vj
import numpy as np
from functools import reduce
from vnmrjpy.core.utils import vprint
import warnings

"""
vnmrjpy.varray
==============

Contaions the main varray object, and the basic k-space and image space
building methods as well as conversion between the two.

"""
class varray():
    """Main vnmrjpy object to carry data and reconstruction information.

    Attributes:
        
    Methods:


    """
    def __init__(self, data=None, pd=None, source=None, is_zerofilled=False,\
                is_kspace_complete=False, fid_header=None, fdf_header=None,\
                nifti_header=None, space=None, intent=None,dtype=None,\
                arrayed_params=[None,1], seqcon=None, apptype=None,\
                vdtype=None):

        self.data = data
        self.pd = pd
        self.source = source
        self.intent = intent
        self.space = space
        self.dtype= dtype
        self.vdtype = vdtype
        self.is_zerofileld = is_zerofilled
        self.is_kspace_complete = is_kspace_complete
        self.fid_header = fid_header
        self.fdf_header = fid_header
        self.nifti_header = nifti_header
        self.arrayed_params = arrayed_params
        self.seqcon = seqcon
        self.apptype = apptype
    
    def set_nifti_header(self):

        return vj.core.niftitools._set_nifti_header(self)

    # put the transforms into another file for better visibility

    def to_local(self):
        """Transform to original space at k-space formation"""
        pass

    def to_scanner(self):
        """Transform data to scanner coordinate space by properly swapping axes

        Standard vnmrj orientation - meaning rotations are 0,0,0 - is axial, with
        x,y,z axes (as global gradient axes) corresponding to phase, readout, slice.
        vnmrjpy defaults to handling numpy arrays of:
                    (readout, phase, slice/phase2, time*echo, receivers)
        but arrays of
                            (x,y,z, time*echo, reveivers)
        is also desirable in some cases (for example registration in FSL flirt,
        or third party stuff)

        Euler angles of rotations are psi, phi, theta.

        Also corrects reversed X gradient and sliceorder
        """
        if vj.core.transform._check_90deg(self.pd):
            pass
        else:
            raise(Exception('Only Euler angles of 0,90,180 are permitted.'))    

        return vj.core.transform._to_scanner(self)

    def to_anatomical(self):
        """Transform to rat brain anatomical coordinate system, the 'usual'"""
        return vj.core.transform._to_anatomical(self)

    def to_global(self):
        """Fixed to scanner, but enlarges FOV if necessary to support oblique.
        """
        return vj.core.transform._to_global(self)

    def to_kspace(self):
        """Build the k-space from the raw fid data and procpar.

        Raw fid_data is numpy.ndarray(blocks, traces * np) format. Should be
        untangled based on 'seqcon' or 'seqfil' parameters.
        seqcon chars refer to (echo, slice, Pe1, Pe2, Pe3)

        PREVIOUS:
                ([rcvrs, phase, read, slice, echo*time])
        NOW:
                ([phase, read, slice, echo*time, rcvrs])
        """
        # if data is not from fid, just fft it
        if self.vdtype == 'imagespace':
            raise(Exception('not implemented yet'))        
            #TODO something like this:

            #self.data = vj.core.recon._fft(self.data,dims)
            #self.vdype = 'kspace'                

        # check if data is really from fid
        if self.vdtype is not 'fid':
            raise(Exception('varray data is not fid data.'))
        self.data = np.vectorize(complex)(self.data[:,0::2],\
                                                self.data[:,1::2])
        # check for arrayed parameters, save the length for later 
        array_length = reduce(lambda x,y: x*y, \
                        [i[1] for i in self.arrayed_params])
        blocks = self.data.shape[0] // array_length
        vprint('Making k-space for '+ str(self.apptype)+' '\
                +str(self.pd['seqfil'])+' seqcon: '+str(self.pd['seqcon']))
        rcvrs = self.pd['rcvrs'].count('y')

        def _is_interleaved(ppdict):
            res  = (int(ppdict['sliceorder']) == 1)
            return res
        def _is_evenslices(ppdict):
            try:
                res = (int(ppdict['ns']) % 2 == 0)
            except:
                res = (int(ppdict['pss']) % 2 == 0)
            return res
        def make_im2D():
            """Child method of 'make', provides the same as vnmrj im2Drecon"""
            p = self.pd 
            rcvrs = int(p['rcvrs'].count('y'))
            (read, phase, slices) = (int(p['np'])//2,int(p['nv']),int(p['ns']))
            if 'ne' in p.keys():
                echo = int(p['ne'])
            else:
                echo = 1
            time = 1
            # this is the old shape which worked, better to reshape at the end
            finalshape = (rcvrs, phase, read, slices,echo*time*array_length)
            final_kspace = np.zeros(finalshape,dtype='complex64')
           
            for i in range(array_length):
 
                kspace = self.data[i*blocks:(i+1)*blocks,...]

                if p['seqcon'] == 'nccnn':
                    shape = (rcvrs, phase, slices, echo*time, read)
                    kspace = np.reshape(kspace, shape, order='C')
                    kspace = np.moveaxis(kspace, [0,1,4,2,3], [0,1,2,3,4])
                    

                elif p['seqcon'] == 'nscnn':

                    raise(Exception('not implemented'))

                elif p['seqcon'] == 'ncsnn':

                    preshape = (rcvrs, phase, slices*echo*time*read)
                    shape = (rcvrs, phase, slices, echo*time, read)
                    kspace = np.reshape(kspace, preshape, order='F')
                    kspace = np.reshape(kspace, shape, order='C')
                    kspace = np.moveaxis(kspace, [0,1,4,2,3], [0,1,2,3,4])

                elif p['seqcon'] == 'ccsnn':

                    preshape = (rcvrs, phase, slices*echo*time*read)
                    shape = (rcvrs, phase, slices, echo*time, read)
                    kspace = np.reshape(kspace, preshape, order='F')
                    kspace = np.reshape(kspace, shape, order='C')
                    kspace = np.moveaxis(kspace, [0,1,4,2,3], [0,1,2,3,4])
                else:
                    raise(Exception('Not implemented yet'))
                if _is_interleaved(p): # 1 if interleaved slices
                    if _is_evenslices(p):
                        c = np.zeros(kspace.shape, dtype='complex64')
                        c[...,0::2,:] = kspace[...,:slices//2,:]
                        c[...,1::2,:] = kspace[...,slices//2:,:]
                        kspace = c
                    else:
                        c = np.zeros(kspace.shape, dtype='complex64')
                        c[...,0::2,:] = kspace[...,:(slices+1)//2,:]
                        c[...,1::2,:] = kspace[...,(slices-1)//2+1:,:]
                        kspace = c

                final_kspace[...,i*echo*time:(i+1)*echo*time] = kspace
            self.data = final_kspace
            return self

        def make_im2Dcs():
            """
            These (*cs) are compressed sensing variants
            """

            def decode_skipint_2D(skipint):

               pass
 
            raise(Exception('not implemented'))

        def make_im2Depi():

            p = self.p
            kspace = self.pre_kspace
            print(kspace.shape)
            nseg = p['nseg']
            kzero = int(p['kzero'])  
            images = int(p['images'])  # repetitions
            time = images
            if p['navigator'] == 'y':
                pluspe = 1 + int(p['nnav'])  # navigator echo + unused
            else:
                pluspe = 1  # unused only
            
            print('images {}'.format(images))
            print('nseg {}'.format(nseg))
            print('ns {}'.format(p['ns']))
            
            if p['pro'] != 0:
                (read, phase, slices) = (int(p['nread']), \
                                            int(p['nphase']), \
                                            int(p['ns']))
            else:
                (read, phase, slices) = (int(p['nread'])//2, \
                                            int(p['nphase']), \
                                            int(p['ns']))
            
            if p['seqcon'] == 'ncnnn':

                preshape = (self.rcvrs, phase+pluspe, slices, time, read)
                print(kspace.size)
                tmp = np.zeros(preshape)
                print(tmp.size)
                kspace = np.reshape(kspace, preshape, order='c')

        def make_im2Depics():
            raise(Exception('not implemented'))
        def make_im2Dfse():

            p = self.pd
            #petab = vj.util.getpetab(self.procpar,is_procpar=True)
            petab = vj.core.read_petab(self.pd)
            nseg = int(p['nseg'])  # seqgments
            etl = int(p['etl'])  # echo train length
            kzero = int(p['kzero'])  
            images = int(p['images'])  # repetitions
            (read, phase, slices) = (int(p['np'])//2,int(p['nv']),int(p['ns']))

            # setting time params
            echo = 1
            time = images

            phase_sort_order = np.reshape(np.array(petab),petab.size,order='C')
            # shift to positive
            phase_sort_order = phase_sort_order + phase_sort_order.size//2-1

            finalshape = (rcvrs, phase, read, slices,echo*time*array_length)
            final_kspace = np.zeros(finalshape,dtype='complex64')
           
            for i in range(array_length):
 
                kspace = self.data[i*blocks:(i+1)*blocks,...]
                if p['seqcon'] == 'nccnn':

                    #TODO check for images > 1
                    preshape = (rcvrs, phase//etl, slices, echo*time, etl, read)
                    shape = (rcvrs, echo*time, slices, phase, read)
                    kspace = np.reshape(kspace, preshape, order='C')
                    kspace = np.swapaxes(kspace,1,3)
                    kspace = np.reshape(kspace, shape, order='C')
                    # shape is [rcvrs, phase, slices, echo*time, read]
                    kspace = np.swapaxes(kspace,1,3)
                    kspace_fin = np.zeros_like(kspace)
                    kspace_fin[:,phase_sort_order,:,:,:] = kspace
                    kspace_fin = np.moveaxis(kspace_fin, [0,1,4,2,3], [0,1,2,3,4])
                    kspace = kspace_fin
                else:
                    raise(Exception('not implemented'))
                
                if _is_interleaved(p): # 1 if interleaved slices
                    if _is_evenslices(p):
                        c = np.zeros(kspace.shape, dtype='complex64')
                        c[...,0::2,:] = kspace[...,:slices//2,:]
                        c[...,1::2,:] = kspace[...,slices//2:,:]
                        kspace = c
                    else:
                        c = np.zeros(kspace.shape, dtype='complex64')
                        c[...,0::2,:] = kspace[...,:(slices+1)//2,:]
                        c[...,1::2,:] = kspace[...,(slices-1)//2+1:,:]
                        kspace = c
            
                final_kspace[...,i*echo*time:(i+1)*echo*time] = kspace
            self.data = final_kspace
            return self

        def make_im2Dfsecs():
            raise(Exception('not implemented'))
        def make_im3D():
            """Child method of 'make', provides the same as vnmrj im3Drecon"""
            p = self.pd 
            rcvrs = int(p['rcvrs'].count('y'))
            (read, phase, phase2) = (int(p['np'])//2,int(p['nv']),int(p['nv2']))
            if 'ne' in p.keys():
                echo = int(p['ne'])
            else:
                echo = 1
            if 'images' in p.keys():
                time = int(p['images'])
            else:
                time = 1

            finalshape = (rcvrs, phase, read, phase2,echo*time*array_length)
            final_kspace = np.zeros(finalshape,dtype='complex64')
           
            for i in range(array_length):
 
                kspace = self.data[i*blocks:(i+1)*blocks,...]

                if p['seqcon'] == 'nccsn':
                
                    preshape = (rcvrs,phase2,phase*echo*time*read)
                    shape = (rcvrs,phase2,phase,echo*time,read)
                    kspace = np.reshape(kspace,preshape,order='F')
                    kspace = np.reshape(kspace,shape,order='C')
                    kspace = np.moveaxis(kspace, [0,2,4,1,3], [0,1,2,3,4])
                    # what is this??
                    #kspace = np.flip(kspace,axis=3)

                if p['seqcon'] == 'ncccn':
                    preshape = (rcvrs,phase2,phase*echo*time*read)
                    shape = (rcvrs,phase,phase2,echo*time,read)
                    kspace = np.reshape(kspace,preshape,order='F')
                    kspace = np.reshape(kspace,shape,order='C')
                    kspace = np.moveaxis(kspace, [0,2,4,1,3], [0,1,2,3,4])
        
                if p['seqcon'] == 'cccsn':
                
                    preshape = (rcvrs,phase2,phase*echo*time*read)
                    shape = (rcvrs,phase,phase2,echo*time,read)
                    kspace = np.reshape(kspace,preshape,order='F')
                    kspace = np.reshape(kspace,shape,order='C')
                    kspace = np.moveaxis(kspace, [0,2,4,1,3], [0,1,2,3,4])

                if p['seqcon'] == 'ccccn':
                    
                    shape = (rcvrs,phase2,phase,echo*time,read)
                    kspace = np.reshape(kspace,shape,order='C')
                    kspace = np.moveaxis(kspace, [0,2,4,1,3], [0,1,2,3,4])

                final_kspace[...,i*echo*time:(i+1)*echo*time] = kspace

            self.data = final_kspace
            
            return self

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
                self.kspace = kspace
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
                kspace = np.moveaxis(kspace, [0,1,4,2,3],[0,1,2,3,4])
                
            self.kspace = kspace
            return kspace

        def make_im3Dute():
            raise(Exception('not implemented')) 
        # ----------------Handle sequence exceptions first---------------------

        vprint(' making seqfil : {}'.format(self.pd['seqfil']))


        if str(self.pd['seqfil']) == 'ge3d_elliptical':
           
            self = make_im3Dcs()

        #--------------------------Handle by apptype---------------------------

        if self.pd['apptype'] == 'im2D':

            self = make_im2D()
            self.is_kspace_complete = True

        elif self.pd['apptype'] == 'im2Dcs':

            self = make_im2Dcs()

        elif self.pd['apptype'] == 'im2Depi':

            self = make_im2Depi()
            self.is_kspace_complete = True

        elif self.pd['apptype'] == 'im2Depics':

            self = make_im2Depics()

        elif self.pd['apptype'] == 'im2Dfse':

            self = make_im2Dfse()
            self.is_kspace_complete = True

        elif self.pd['apptype'] == 'im2Dfsecs':

            self = make_im2Dfsecs()

        elif self.pd['apptype'] == 'im3D':

            self = make_im3D()
            self.is_kspace_complete = True

        elif self.pd['apptype'] == 'im3Dcs':

            self = make_im3Dcs()

        elif self.pd['apptype'] == 'im3Dute':

            self = make_im3Dute()
            self.is_kspace_complete = True

        else:
            raise(Exception('Could not find apptype. Maybe not implemented?'))

        # ---------------------Global modifications on Kspace------------------

        #TODO if slices are in reversed order, flip them
        
        # in revamp make new axes, mainly for nifti io, and viewers
        # old : [rcvrs, phase, read, slice, time]
        # new : [read, phase, slice, time, rcvrs]

        self.data = np.moveaxis(self.data,[0,1,2,3,4],[4,1,0,2,3])
        # swap axes 0 and 1 so phase, readout etc is the final order
        self.data = np.swapaxes(self.data,0,1)
        self.space='local'
        self.vdtype='kspace'
        self.sdims = ['phase','read','slice','time','rcvr']
        self.set_nifti_header()


        if vj.config['default_space'] == None:
            pass
        elif vj.config['default_space'] == 'anatomical'
            pass
        elif vj.config['default_space'] == 'scanner'
            pass
        
        return self

    def to_imagespace(self):
        """ Reconstruct MR images to real space from k-space.

        Generally this is done by fourier transform and corrections.
        Hardcoded for each 'seqfil' sequence.

        Args:

        Updates attributes:
            data
            

        """
        seqfil = str(self.pd['seqfil'])
        # this is for fftshift
        ro_dim = self.sdims.index('read')  # this should be default
        pe_dim = self.sdims.index('phase')  # this should be default
        pe2_dim = self.sdims.index('slice')  # slice dim is also pe2 dim
        
        sa = (ro_dim, pe_dim, pe2_dim)

        if seqfil in ['gems', 'fsems', 'mems', 'sems', 'mgems']:

            self.data = vj.core.recon._ifft(self.data,sa[0:2])

        elif seqfil in ['ge3d','fsems3d','mge3d']:
            
            self.data = vj.core.recon._ifft(self.data,sa)

        elif seqfil in ['ge3d_elliptical']:

            self.data = vj.core.recon._ifft(self.data,sa)

        else:
            raise Exception('Sequence reconstruction not implemented yet')
        
        self.vdtype = 'imagespace'

        return self
