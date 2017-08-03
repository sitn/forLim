# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 09:17:25 2015

@author: SFFN/MRu
"""

# import modules
from osgeo import gdal, ogr, osr, gdalconst
import numpy as np
import scipy.ndimage
import copy
import math
import os
import gc

def main(args):

    files = args['Path_input'].split(';')

    for f in enumerate(files):

        f_name = os.path.basename(f[1]).split('.tif')[0]

        #########################
        #  0. Read input image  #
        #########################
        # open dataset
        dataset = gdal.Open(f[1], gdalconst.GA_ReadOnly)
        cols = dataset.RasterXSize
        rows = dataset.RasterYSize

        # georeference
        geotransform = dataset.GetGeoTransform()
        prj_wkt = dataset.GetProjectionRef()

        # extract raster values
        band = dataset.GetRasterBand(1)
        data = band.ReadAsArray(0, 0, dataset.RasterXSize, dataset.RasterYSize)

        ###########################################
        #  1. Determine forest areas iteratively  #
        ###########################################
        data_FD, data_PB = iterativeMethod(data,args)

        #################################
        #  2. Export files TIF and SHP  #
        #################################
        #Dense forest (FD)
        dst_tif = os.path.join(args['Path_output_tiles'], f_name + '_binary_FD.tif')
        dst_shp = os.path.join(args['Path_output_tiles'], f_name + '_FD.shp')
        drawPolygons(data_FD,dataset,cols,rows,geotransform,prj_wkt,dst_tif,dst_shp)

        #Wooded pasture (PB)
        dst_tif = os.path.join(args['Path_output_tiles'], f_name + '_binary_PB.tif')
        dst_shp = os.path.join(args['Path_output_tiles'], f_name + '_PB.shp')
        drawPolygons(data_PB,dataset,cols,rows,geotransform,prj_wkt,dst_tif,dst_shp)


# transform map coordinates (x,y) to image coordinates (col,row)
def mapToPixel(mx,my,gt):
    """ Convert map to pixel coordinates
        @param  mx    Input map x coordinate (double)
        @param  my    Input map y coordinate (double)
        @param  gt    Input geotransform (six doubles)
        @return px,py Output coordinates (two doubles)
    """
    if gt[2]+gt[4]==0: #Simple calc, no inversion required
        px = (mx - gt[0]) / gt[1]
        py = (my - gt[3]) / gt[5]
    else:
        px,py=ApplyGeoTransform(mx,my,InvGeoTransform(gt))
    return int(px+0.5),int(py+0.5)


# transform image coordinates (col,row) to map coordinates (x,y)
def pixelToMap(px,py,gt):
    """ Convert pixel to map coordinates
        @param  px    Input pixel x coordinate (double)
        @param  py    Input pixel y coordinate (double)
        @param  gt    Input geotransform (six doubles)
        @return mx,my Output coordinates (two doubles)
    """
    mx,my=ApplyGeoTransform(px,py,gt)
    return mx,my


def ApplyGeoTransform(inx,iny,gt):
    """ Apply a geotransform
        @param  inx       Input x coordinate (double)
        @param  iny       Input y coordinate (double)
        @param  gt        Input geotransform (six doubles)
        @return outx,outy Output coordinates (two doubles)
    """
    outx = gt[0] + inx*gt[1] + iny*gt[2]
    outy = gt[3] + inx*gt[4] + iny*gt[5]
    return (outx,outy)


# cartestian to polar coordinates
def cart2pol(x, y):
    theta = np.arctan2(y, x)
    rho = np.sqrt(x**2 + y**2)
    return (theta, rho)  


# compute image gradient
def grad2d(dem,dx,dy):
    fy, fx = np.gradient(dem,dx,dy)
    asp, grad = cart2pol(fy,fx)
    grad = np.arctan(grad)
    asp = -asp + math.pi
    return grad, asp


# create circular kernel
def createKernel(radius):
    radius = int(radius)
    kernel = np.zeros((2*radius+1, 2*radius+1))
    y,x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = x**2 + y**2 <= radius**2
    kernel[mask] = 1
    return kernel


def InvGeoTransform(gt_in):
    # Compute determinate
    det = gt_in[1] * gt_in[5] - gt_in[2] * gt_in[4]
    if( abs(det) < 0.000000000000001 ):
        return
    inv_det = 1.0 / det

    # compute adjoint, and divide by determinate
    gt_out = [0,0,0,0,0,0]
    gt_out[1] =  gt_in[5] * inv_det
    gt_out[4] = -gt_in[4] * inv_det
    gt_out[2] = -gt_in[2] * inv_det
    gt_out[5] =  gt_in[1] * inv_det
    gt_out[0] = ( gt_in[2] * gt_in[3] - gt_in[0] * gt_in[5]) * inv_det
    gt_out[3] = (-gt_in[1] * gt_in[3] + gt_in[0] * gt_in[4]) * inv_det
    return gt_out


# Fill clearings smaller than threshold
def filterClearings(ima, args):
#    se = scipy.ndimage.generate_binary_structure(2,2)
    se = None
    label_im_clearings, nb_labels_clearings = scipy.ndimage.label(~ima, structure=se, output=int) ## structure = None
    sizes_clearings = scipy.ndimage.sum(~ima, label_im_clearings, range(nb_labels_clearings + 1))
    clearings_idx = sizes_clearings < args["HoleSizeThres"]
    clearings_remove_pixel = clearings_idx[label_im_clearings]
    ima[clearings_remove_pixel] = True
    return ima


# Remove islands smaller than threshold
def filterIslands(ima, args):
#    se = scipy.ndimage.generate_binary_structure(2,2)
    se = None
    label_im_clearings, nb_labels_clearings = scipy.ndimage.label(ima, structure=se, output=int) ## structure = None
    sizes_clearings = scipy.ndimage.sum(ima, label_im_clearings, range(nb_labels_clearings + 1))
    clearings_idx = sizes_clearings < args["MinAreaThres"]
    clearings_remove_pixel = clearings_idx[label_im_clearings]
    ima[clearings_remove_pixel] = False
    return ima


# Remove hedge that are thinner than threshold    
def filterHedges(ima, se):
    ima = scipy.ndimage.morphology.binary_opening(ima, structure=se, iterations=1, origin=0)
#    ima = scipy.ndimage.morphology.binary_opening(ima, structure=se, iterations=2, origin=0)
    return ima


# Combined morphological filters
def morphoFilter(ima, args, se):
    ima = filterClearings(ima, args)
    ima = filterIslands(ima, args)
    ima = filterHedges(ima, se)
    return ima


# Proceed iterative method    
def iterativeMethod(data,args):
    # Ig = copy.copy(data)
    print 'iterativeMethod'

    # apply mean height convolution
    se = createKernel(np.ceil(args["GradConvDiameter"]/2))
    se = se/np.sum(se)
    data = scipy.ndimage.filters.convolve(data, se, mode="constant", cval=0.0)

    # compute image gradient
    # to make a first approximation of forest areas
    data[(data <= args['MinHeightThres']) | (data >= args['MaxHeightThres'])] = 0.0
    fy, fx = np.gradient(data,1,1)
    asp, grad = cart2pol(fy,fx)

    # filter gradient mask by applying an intensity threshold
    gradmask = np.zeros(grad.shape).astype(bool)
    gradmask[grad > 0.7] = True

    # remove clearings from gradmask
    gradmask = filterClearings(gradmask, args)

    a = gradmask.copy()

    # separate small elements and large ones
    grad_label, nlabel = scipy.ndimage.measurements.label(a, output=int)
    sizes_elements = scipy.ndimage.sum(a, grad_label, range(nlabel + 1))   #compute the amount of pixels contained in each label, kowing that 1px is 1m2
    small_idx = sizes_elements >= args["MinAreaBigElem"]
    large_idx = sizes_elements = ~small_idx
    remove_small_pixel = large_idx[grad_label]
    remove_large_pixel = small_idx[grad_label]
    gradmaskL = gradmask.copy()
    gradmaskL[remove_small_pixel] = False
    gradmaskS = gradmask.copy()
    gradmaskS[remove_large_pixel] = False

    # find coutours of objects in large elements
    a = gradmaskL.copy()
    dx,dy = np.gradient(a)
    a = np.sqrt(dx**2 + dy**2)
    a = a>0

    # dilate contours and get edge
    se = createKernel(args["BorderWidth"])
    borderMask = np.bitwise_and(gradmaskL, scipy.ndimage.morphology.binary_dilation(a, structure=se))

    #connect dilated contours and small elements
    a = np.bitwise_or(borderMask,gradmaskS).astype(float)

    #filter image
    weights = createKernel(np.ceil(args["CW_diameter"]/2))
    weights = weights/np.sum(weights)
    a = scipy.ndimage.filters.convolve(a, weights=weights, mode="constant", cval=0.0)

    se = createKernel(np.ceil(args["BorderWidth"]/2))
    a_FD = scipy.ndimage.morphology.binary_opening(a>args["Deg_Recouv_FD"], se)
    a_PB = scipy.ndimage.morphology.binary_opening(a>args["Deg_Recouv_PB"], se)

    b = [a_FD, a_PB]

    #Let call a the input image corresponding to the overlap test and A the filtered output
    A = list()
    for a in b:

        gradmask = np.bitwise_or(a, gradmaskL)

        # define circular opening structuring element
        kernel_hedge = createKernel(np.ceil(args['WidthThres']/2))

        # repeat morphological operations until no change appears
        iterate = True
        new_ima = copy.copy(gradmask)

        while iterate:
            old_ima = copy.copy(new_ima)
            new_ima = morphoFilter(copy.copy(old_ima), args, kernel_hedge)
            iterate = not np.array_equal(old_ima, new_ima)

        A.append(new_ima)

    return A[0], A[1]


# Verify the overlap level
def forestOverlap(M,cw,args):
    M = (M>0).astype(float)
    M = scipy.ndimage.filters.convolve(M, cw, mode="constant", cval=0.0)
    M_FD = (M>=args["Deg_Recouv_FD"])
    M_PB = (M>=args["Deg_Recouv_PB"])
    return M_FD, M_PB


# Determine which pixel is forest or not based on forestOverlap criteria
def forestDetermination(data,args):
    cw = createKernel(np.ceil(args["CW_diameter"]/2))
    Ncw = np.sum(cw)
    cw = cw/Ncw
    
    data_FD, data_PB = forestOverlap(data,cw,args)
    return data_FD, data_PB


# Generate tif and shp files
def drawPolygons(new_ima,dataset,cols,rows,geotransform,prj_wkt,path_tif,path_shp):
    # initialize output raster layer
    if os.path.exists(path_tif):
        os.remove(path_tif)
    n_bands = dataset.RasterCount
    dst_raster_filepath = path_tif
    dst_raster = gdal.GetDriverByName("GTiff").Create(dst_raster_filepath, cols, rows, n_bands, gdal.GDT_Byte)
    dst_raster.SetGeoTransform(geotransform)
    dst_raster.SetProjection(prj_wkt)
    dst_raster.GetRasterBand(1).WriteArray(new_ima.astype(bool))
    dataset.FlushCache()  # Write to disk.
    
    # initialize output OGR vector layer
    if os.path.exists(path_shp):
        os.remove(path_shp)
    spatialRef = osr.SpatialReference(wkt=prj_wkt)
#    spatialRef.ImportFromEPSG(21781) ################## fonctionne que pour CH1903
    dst_vector_filepath = path_shp
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dst_vector = driver.CreateDataSource(dst_vector_filepath)
    dst_layer = dst_vector.CreateLayer(os.path.splitext(os.path.basename(dst_vector_filepath))[0], srs = spatialRef)
    
    # trace edges
    gdal.Polygonize(dst_raster.GetRasterBand(1), dst_raster.GetRasterBand(1), dst_layer, -1, [], callback=None)
    dst_vector.Destroy()



__Author__ = "SFFN/MRu"
__Version__ = "1.0"
__Date__ = "01.07.2015"

