import os
import shutil
import numpy as np
import time

from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from shapely.geometry import MultiPolygon, Polygon
import rasterio as rio
from rasterio.plot import show
import rasterio.mask
import fiona
import folium

from geojson import Polygon
import json

import zipfile

class EachBandFig(object):
    def __init__(self,location,width,height,name,
                 start_date="20190101",end_date="20190128",
                 platformname="Sentinel-2",processinglevel = 'Level-2A'):

        os.makedirs('./data_geo', exist_ok=True)                  ##衛星画像データを保存するディレクトリ
        os.makedirs('./{}/Image_tiff'.format(name), exist_ok=True)##処理済みデータを保存するディレクトリ
        os.makedirs('./location', exist_ok=True)                  ##位置情報を保存するディレクトリ

        self.AREA = return_AREA(left_top=location,width=width,height=height) #緯度経度+縦横の範囲をリスト化
        self.name = name
        get_polygon(self.AREA,self.name) #ポリゴンデータをlocationの中に生成

        #位置情報から衛星画像をダウンロードもしくは取得
        self.title = get_data(self.name,self.AREA,
                                  start_date=start_date,end_date=end_date,
                                  platformname=platformname,processinglevel=processinglevel)

        #解像度ごとにbandのデータを分けて、辞書に保存
        self.r10m = {}
        self.r20m = {}
        self.r60m = {}

        for b in ["02","03","04","08"]:
            self.r10m[b]=crop(self.title,self.name,"10m",b)
        for b in ["02","03","04","05","06","07","8A","11","12"]:
            self.r20m[b]=crop(self.title,self.name,"20m",b)
        for b in ["01","02","03","04","05","06","07","8A","09","11","12"]:
            self.r60m[b]=crop(self.title,self.name,"60m",b)

        #衛星画像のメタデータを取得
        self.meta = crop(self.title,self.name,"10m","02",meta=True)
        self.map = get_map(self.AREA,self.name) #地図上での表示


############# Following methods calculate certaion index ########################
    def ndwi_3_8(self,thresh=False,figsize=(10,10),resolution=10,array=True,store=False):
        val = ratio(self,index="ndwi_3_8",
                b_1=self.r10m["03"],b_2=self.r10m["08"],
                thresh=thresh,figsize=figsize,array=array,store=store)
        if array:
            return val

    def ndwi_4_11(self,thresh=False,figsize=(10,10),resolution=20,array=True,store=False):
        val = ratio(self,index="ndwi_4_11",
                b_1=self.r20m["04"],b_2=self.r20m["11"],
                thresh=thresh,figsize=figsize,array=array,store=store)
        if array:
            return val

    def mo_ind(self,thresh=False,figsize=(10,10),resolution=20,array=True,store=False):
        val = ratio(self,index="mo_ind",
                b_1=self.r20m["8A"],b_2=self.r20m["11"],
                thresh=thresh,figsize=figsize,array=True,store=store)
        if array:
            return val

    def ndvi(self,thresh=False,figsize=(10,10),resolution=10,array=True,store=False):
        val = ratio(self,index="ndvi",
                b_1=self.r10m["04"],b_2=self.r10m["08"],
                thresh=thresh,figsize=figsize,array=True,store=store)
        if array:
            return val

    def ndsi(self,thresh=False,figsize=(10,10),resolution=20,array=True,store=False):
        val = ratio(self,index="ndsi",
                b_1=self.r20m["03"],b_2=self.r20m["11"],
                thresh=thresh,figsize=figsize,array=True,store=store)
        if array:
            return val

    def truecolor(self,
                b_thresh=False,g_thresh=False,r_thresh=False,
                figsize=(10,10),array=True):
        val = bgr(self,index="true",
                blu=self.r10m["02"],
                gre=self.r10m["03"],
                red=self.r10m["04"],
                b_thresh=b_thresh,g_thresh=g_thresh,r_thresh=r_thresh,
                figsize=figsize,array=array)
        if array:
            return val

    def falsecolor(self,
                b_thresh=False,g_thresh=False,r_thresh=False,
                figsize=(10,10),array=True):
        val = bgr(self,index="false",
                blu=self.r10m["03"],
                gre=self.r10m["04"],
                red=self.r10m["08"],
                b_thresh=b_thresh,g_thresh=g_thresh,r_thresh=r_thresh,
                figsize=figsize,array=array)
        if array:
            return val

    def swir(self,
                b_thresh=False,g_thresh=False,r_thresh=False,
                figsize=(10,10),array=True):
        val = bgr(self,index="swir",
                blu=self.r20m["04"],
                gre=self.r20m["8A"],
                red=self.r20m["12"],
                b_thresh=b_thresh,g_thresh=g_thresh,r_thresh=r_thresh,
                figsize=figsize,array=array)
        if array:
            return val

    def natural(self,
                b_thresh=False,g_thresh=False,r_thresh=False,
                figsize=(10,10),array=True):
        val = bgr(self,index="natural",
                blu=self.r10m["02"],
                gre=self.r10m["04"],
                red=self.r10m["03"],
                b_thresh=b_thresh,g_thresh=g_thresh,r_thresh=r_thresh,
                figsize=figsize,array=array)
        if array:
            return val

    def agr(self,
                b_thresh=False,g_thresh=False,r_thresh=False,
                figsize=(10,10),array=True):
        val = bgr(self,index="agr",
                blu=self.r20m["02"],
                gre=self.r20m["8A"],
                red=self.r20m["11"],
                b_thresh=b_thresh,g_thresh=g_thresh,r_thresh=r_thresh,
                figsize=figsize,array=array)
        if array:
            return val

####### Following functions request data from sentinel api##################3
def return_AREA(left_top=[137.383727,34.751157],width=0.0326,height=0.0195):
    AREA =[]
    AREA.append([left_top[0],left_top[1]])
    AREA.append([left_top[0],left_top[1]-height])
    AREA.append([left_top[0]+width,left_top[1]-height])
    AREA.append([left_top[0]+width,left_top[1]])
    AREA.append([left_top[0],left_top[1]])
    return AREA

def get_polygon(AREA,name):
    m=Polygon([AREA])
    #位置情報をjsonデータとして保存
    with open('./location/' + str(name) +'.geojson', 'w') as f:
        json.dump(m, f)

def get_data(name,AREA,start_date= '20190101',end_date='20190128',
    platformname='Sentinel-2',processinglevel = 'Level-2A'):
    #apiのクエリに次のが必要。中身はPOLYGON((..))っていうstr型
    footprint_geojson = geojson_to_wkt(read_geojson('./location/' + str(name) +'.geojson'))
    # use sentinelAPI
    user = ''
    password = ''
    api = SentinelAPI(user, password, 'https://scihub.copernicus.eu/dhus')

    products = api.query(footprint_geojson,
                         date = (start_date, end_date), #取得希望期間の入力
                         platformname = platformname,
                         processinglevel = processinglevel,##2016年はL1C
                         cloudcoverpercentage = (0,100)) #被雲率（0％〜100％）
    print("この期間の画像の数は" + str(len(products)) +"枚です")

    #この後で雲の被覆率ごとにデータを並べ替えて、1個ダウンロードする。
    products_gdf = api.to_geodataframe(products)
    products_gdf_sorted = products_gdf.sort_values(['cloudcoverpercentage'], ascending=[True]).head()
    #ファイルがまだなければデータダウンロード。作業ディレクトリにzipファイルがダウンロードされる

    for i in range(3): #3回までチャレンジ
        uuid = products_gdf_sorted.iloc[i]["uuid"]
        product_title = products_gdf_sorted.iloc[i]["title"]  #S2A_MSIL2A_20190101T01405... みたいな
        product_date = products_gdf_sorted.iloc[i]["summary"].split(',')[0].split()[1][:10]
        print("この期間で1番被覆率が低いのは"+product_date+"日")

        if os.path.isfile("./data_geo/"+str(product_title) +'.zip') != True:
            print("新規にデータをダウンロードします")
            try:
                api.download(uuid)
            except:
                print("ダウンロード不可")
            else:
                break
        else:
            break

    if os.path.isfile("./data_geo/"+str(product_title) +'.zip') != True:
        #ダウンロードしたzipファイルを解凍
        #str(product_title) + '.SAFE っていうフォルダが生成される
        file_name = str(product_title) +'.zip'
        with zipfile.ZipFile(file_name) as zf:
                zf.extractall()
        shutil.move(str(product_title) +'.zip', './data_geo/')
        shutil.move(str(product_title) +'.SAFE', './data_geo/')

    return product_title

def get_path(product_title,r="10m",band="02"):
    #product_titleはダウンロードしたデータのフォルダ名
    #rは分解能__m,bandは波長

    root = "./data_geo"
    #ここからフォルダの中に潜っていく
    path = os.path.join(root,str(product_title)+".SAFE","GRANULE")
    files = os.listdir(path)

    pathA = os.path.join(path,str(files[0]))
    files2 = os.listdir(pathA)

    #files2[1]はIMG_DATA
    try:
        pathB = os.path.join(pathA,"IMG_DATA","R"+r)
        files3 = os.listdir(pathB)

        path_b = os.path.join(pathB,str(files3[0][0:23] +'B{}_{}.jp2'.format(band,r)))
        return path_b

    except FileNotFoundError:
        pathB = os.path.join(pathA,"IMG_DATA")
        files3 = os.listdir(pathB)
        path_b = os.path.join(pathB,str(files3[0][0:23] +'B{}.jp2'.format(band)))
    return path_b

#選んだバンドの画像をトリミングしてImage_tiffに保存
def crop(title,name,r,band,store=False,meta=False):
    nReserve_geo = gpd.read_file('./location/' + str(name) +'.geojson')
    path = get_path(title,r=r,band=band)
    original_bandfig = rio.open(path)

    epsg = original_bandfig.crs
    nReserve_proj = nReserve_geo.to_crs({'init': epsg})

    out_image, out_transform = rio.mask.mask(original_bandfig, nReserve_proj.geometry,crop=True)
    out_meta = original_bandfig.meta.copy()
    out_meta.update({"driver": "GTiff",
             "height": out_image.shape[1],
             "width": out_image.shape[2],
             "transform": out_transform})
    if store:
        with rio.open("./{}/Image_tiff/Cropped_".format(name)+band+"Image.tiff", "w", **out_meta) as dest:
            dest.write(out_image)

    if meta:
        return out_meta
    else:
        return out_image

####指定したpolygonの範囲を地図上に表示
def get_map(AREA,name):
    m=folium.Map([(AREA[0][1]+AREA[len(AREA)-1][1])/2,
            (AREA[0][0]+AREA[len(AREA)-1][0])/2], zoom_start=10)
    folium.GeoJson('./location/' +str(name) +'.geojson').add_to(m)
    return m


###### Following funtction is for calculation  ########3

def ratio(self,index,b_1=None,b_2=None,thresh=False,figsize=(10,10),resolution=10,array=True,store=False):
    #threshはリストで渡してください[min,max]
    #rasterioデータの演算
    band1 = b_1.astype('float64')
    band2 = b_2.astype('float64')
    #ndwi calculation, empty cells or nodata cells are reported as 0
    ratio_array = np.where((band1+band2)==0., 0, (band1-band2)/(band1+band2))
    area_size = ratio_array.size/1000000
    water_size = 0

    if thresh:
        #閾値処理
        ratio_array =np.where((thresh[0]<ratio_array)&(ratio_array<thresh[1]),ratio_array,0)
        water_size = np.count_nonzero((thresh[0]<ratio_array)&(ratio_array<thresh[1])&(ratio_array!=0))/1000000
    else:
        water_size = np.count_nonzero(ratio_array>0)/1000000

    #面積を計算
    if resolution == 10:
        area_size = area_size*100
        water_size = water_size*100
    if resolution == 20:
        area_size = area_size*400
        water_size = water_size*400
    if resolution == 60:
        area_size = area_size*3600
        water_size = water_size*3600

    print("写ってる範囲の面積 = " + str(area_size)+"km2")
    print("値が0以上の面積 = " + str(water_size)+"km2")
    print("0以上の割合 = " + str((water_size/area_size)*100)+"%")

    fig = plt.figure(figsize=figsize)
    plt.title(str(index))
    show(ratio_array)
    rio.plot.show_hist(ratio_array, bins=50,
       lw=0.0, stacked=False, alpha=0.8, histtype='stepfilled', title="Histogram")

    if store:
        #export ndwi image
        image = rio.open("./{}/{}.tiff".format(self.name,index),
        'w',driver='Gtiff',
        width= self.meta["width"],
        height = self.meta["height"],
        count=1, crs=self.meta["crs"],
        transform=self.meta["transform"],
        dtype='float64')
        image.write(ratio_array[0],1)
        image.close()

    if array:
        return ratio_array

def bgr(self,index,blu=None,gre=None,red=None,
        b_thresh=False,g_thresh=False,r_thresh=False,
        figsize=(10,10),array=True):
    #export false color image
    if b_thresh:
        blu=np.where((b_thresh[0]<blu)&(blu<b_thresh[1]),blu,0)
    if g_thresh:
        gre=np.where((g_thresh[0]<gre)&(gre<g_thresh[1]),gre,0)
    if r_thresh:
        red=np.where((r_thresh[0]<red)&(red<r_thresh[1]),red,0)

    bgr = rio.open('./{}/'.format(self.name)+'{}.tiff'.format(index),'w',driver='Gtiff',
                     width=self.meta["width"], height=self.meta["height"],
                     count=3,
                     crs=self.meta["crs"],
                     transform=self.meta["transform"],
                     dtype=self.meta["dtype"])
    bgr.write(blu[0],3) #Blue
    bgr.write(gre[0],2) #Green
    bgr.write(red[0],1) #Red
    bgr.close()
    bgr_assemble = rio.open('./{}/'.format(self.name)+'{}.tiff'.format(index), count=3)
    fig = plt.figure(figsize=figsize)
    plt.title(str(index))
    show(bgr_assemble)
    rio.plot.show_hist(bgr_assemble,bins=50,lw=0.0, stacked=False, alpha=0.8, histtype='stepfilled', title="Histogram")

    if array:
        return bgr_assemble.read(1)
