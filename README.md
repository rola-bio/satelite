# できること
欧州宇宙機関(ESA)が展開しているSentinel HubからSentinel衛星シリーズの1つであるSentinel-2から衛星画像を取得し、加工できる。
Sentinel-2以外もリクエストできるけれど、基本Sentinel-2用にコードを書いています。

## 事前準備

sentinel APIを使用するために下記のサイトにアクセスして、sign up。
ユーザー名とパスワードを取得します。
https://scihub.copernicus.eu/dhus/

詳細はこちらの記事を参考にされたし
https://sorabatake.jp/9987/

## 依存パッケージのインストール
    $ pip install sentinelsat
    $ pip install geopandas
    $ pip install rasterio
    $ pip install shapely
    $ pip install fiona
    $ pip install folium
    $ pip install geojson
jupyter から実行するときは!pip にすればok!

## 登録ユーザ情報の入力
satelite.pyの176,177行目の
    user = ''
    password = ''
に取得したユーザー名とパスワードを入力する。

# 実行
sample.ipynbの通りです。
こんな感じで画像をゲットできます。

![togo town](/sample.png)

## 終わりに
自分で閾値設定とかいりませんでしたら、EO browzerの方が使いやすいです。
でも各バンドデータを組み合わせて色々したかったら、APIを使わないといけません。

今回のファイルはほぼrasterioっていうパッケージで加工したものです。
下のページを参考にしました。
https://www.hatarilabs.com/ih-en/ndvi-calculation-from-landsat8-images-with-python-3-and-rasterio-tutorial

ちなみにtellusの開発環境(jupyter lab)を申し込んで使えば、依存パッケージをわざわざインストールしなくてすみます。
