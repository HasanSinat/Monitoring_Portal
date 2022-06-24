from email import message
import secretsx
from operator import index
from unicodedata import name
from attr import field
import streamlit as st
import pandas as pd
import numpy as np
from cmath import pi
from datetime import datetime, time
from calendar import month
from optparse import Values
from turtle import clear
import requests, datetime
import sys
import pandas as pd
import requests
import json
import altair as alt
import datetime as dt
import io
import xlsxwriter
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from streamlit_lottie import st_lottie
from streamlit_lottie import st_lottie_spinner

st.set_page_config(page_title="Fixente Portal",layout="wide")
st.sidebar.title('Fixente Portal')
pd.set_option('display.max_rows', None)
dateTime_format = "%Y-%m-%d %H:%M:%S"
options_disabled = False
reactive_daily=False
ac_data_obtained = False
base_url = "https://server.convert-control.de/api"
buffer = io.BytesIO()
buffer_Y = io.BytesIO()
buffer_Z = io.BytesIO()
convertControlPlants = secretsx.convertControlPlants
def get_key(val):
    for plant in convertControlPlants:
         if plant["name"] == val:
             return plant["id"]
    return "key doesn't exist"
def login():
    url = f"{base_url}/login_check"
    payload = json.dumps({
    "username": secretsx.username,
    "password": secretsx.password
    })
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload).json()
    key = response["token"]
    return key
@st.experimental_memo
def fetchData(siteID,startDate,endDate,daily):                
    if daily :
        url = f"{base_url}/yield_log_day?plant={siteID}&timestamp={startDate}&end={endDate + datetime.timedelta(days=1)}"            
    else:
        url = f"{base_url}/yield_log?plant={siteID}&timestamp={startDate} 08:00:00&end={endDate} 21:00:00&selected_timeframe=day"
    
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {key}' }
    response = requests.request("GET", url, headers=headers, ).json()
    response = json.dumps(response)
    response = pd.read_json(response)
    response.drop(columns=['plant','id','yieldPerKwP'] ,inplace=True)
    response["id"] = response["device"]
    response['id'] = response['id'].str[21:] 

    return response
@st.experimental_memo
def fetchReactiveData  (siteID,startDate,endDate,):
    url = f"{base_url}/qmeter_logs?plant={siteID}&timestamp={startDate} 08:00:00&end={endDate} 21:00:00"
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {key}' }
    response = requests.request("GET", url, headers=headers, ).json()
    response = json.dumps(response)
    response = pd.read_json(response)
    reactive = response[['timestamp','CosPhi1', 'CosPhi2','CosPhi3']]
    return reactive
@st.experimental_memo
def dataOrginizer (response, aralik,reverse_bool):
    response = fetchData(siteID,startDate,endDate,is_it_daily)
    #response['timestamp'] = pd.to_datetime(response['timestamp'])
    #response = response.groupby([pd.Grouper(freq='5min', key='timestamp'), 'id']).sum().reset_index()
    response["Tarih"] = response['timestamp']
    #response["Tarih"] = response["Tarih"].dt.strftime("%Y-%m-%d %H:%M:%S")
    response = response.pivot(index="Tarih", columns="id",values="yield",)
    response.sort_index(ascending= reverse_bool, inplace=True)
    response ["Toplam-Üretim-(kW/h)"] = response.sum(axis=1)
    if not is_it_daily:
        response = response.between_time('08:00','19:00')
    response['Fark'] = response['Toplam-Üretim-(kW/h)'].diff()
    response = response[::aralik]
    #response["timestamp"] = pd.to_datetime(response["timestamp"])
    #response = response.groupby([pd.Grouper(freq='H', key='timestamp'), 'id']).sum().reset_index()
    #print(response[24:1000:12])
    response.fillna(0, inplace=True) 
    return response
@st.experimental_memo
def fetch_AC_Data(siteID, startDate,endDate,):
    url = f"{base_url}/dc_points?plant={siteID}&timestamp={startDate} 08:00:00&end={endDate} 21:00:00&devices=338"

    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {key}' }
    response = requests.request("GET", url, headers=headers, ).json()
    response = json.dumps(response)
    response = pd.read_json(response)
    response.fillna(0, inplace=True)
    response = response [['id', 'timestamp','p','index']]
    response = response.set_index("timestamp")
    response = response.between_time("06:30" , "19:00")
    ac_grouped = response.copy()
    ac_grouped=ac_grouped.between_time("08:30" , "19:00")
    ac_grouped.reset_index(inplace=True)
    response.reset_index(inplace=True)
    #ac_grouped.between_time("08:30" , "19:00")  
    response["id"]=response["id"].str[11:]
    response = response.pivot(index="timestamp", columns=["id",],values="p")

    #response = response.asfreq('30T')
    #response.set_index("timestamp", inplace=True)
    
    return response, ac_grouped ,


def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def date_to_str(date,format):
    date = date.dt.strftime(format)
    return date
def dateTime_to_Date(date_as_Str):
    date_as_Str = date_as_Str.str[:10]
    return date_as_Str
def inverter_fig(ac_data):
    ac_data.reset_index(inplace=True)
    ac_inverters = ac_data.drop("timestamp", axis=1)
    inverters_list = ac_inverters.columns.values.tolist()
    try:
        inverters_list.remove("index")
    except :
        pass
    if "selected_inverters" not in st.session_state:
        st.session_state["selected_inverters"] = inverters_list
  
    with st.form(key="InvForm"):
        st.session_state["selected_inverters"] = st.multiselect(
                    "Görüntülenecek Inverterleri Seçiniz.",
                    options=inverters_list,
                    default=inverters_list[:]     
                )
        st.form_submit_button("Submit" ,)   

    fig_ac = px.line(ac_data, x="timestamp", y=st.session_state["selected_inverters"],
                width = 1000,
                height=500,
                title='Inverter Güç Değerleri')
    fig_ac.update_layout(  margin=dict(
        l=50,
        r=30,
        b=100,
        t=80,
        pad=4
    ),)
    st.plotly_chart(fig_ac, use_container_width=True)
@st.experimental_memo
def ac_data_orginizer ():
    ac_grouped = fetch_AC_Data(siteID,startDate,endDate,)[1]
    ac_grouped["id"]=ac_grouped["id"].str[11:14]
    ac_grouped = ac_grouped.pivot(index=["timestamp","id"], columns=["index"],values="p")
    ac_grouped['Fark'] = ((ac_grouped[1] - ac_grouped[2]) / ac_grouped[1] * 100).fillna(0)
    ac_grouped_mppt = ac_grouped.query('Fark > 30 or Fark < -30')
    ac_grouped_mppt.index = ac_grouped_mppt.index.swaplevel()
    ac_grouped_mppt = ac_grouped_mppt.sort_index()
    ac_grouped_zero =  ac_grouped.loc[ac_grouped[1] == 0 ]
    return ac_grouped_mppt, ac_grouped_zero , ac_grouped
@st.experimental_memo
def nonDataDates():
    dates_between = pd.date_range(start= startDate ,end=endDate, freq="5T") 
    dates_between_dframe = pd.DataFrame(index = dates_between)
    dates_between_dframe = dates_between_dframe.between_time('08:00','19:00')
    dates_between_dframe["Kayıp"] = " "
    non_data_index = dates_between_dframe.index.difference(response.index)
    non_Data_F = non_data_index.to_frame(index=False, name="Tarih")
    non_Data_F["Tarih"] = date_to_str(date=non_Data_F["Tarih"], format=dateTime_format)
    non_Data_F["Üretim Kaybı"] = non_Data_F["Tarih"].str[11:16]
    responseLoses = response[response["Fark"] > 0 ] 
    non_Data_F["Üretim Kaybı"] = non_Data_F["Üretim Kaybı"].apply(lambda x : responseLoses['Fark'].at_time(x).mean())
    non_Data_F['Tarih'] = pd.to_datetime(non_Data_F.Tarih, format=dateTime_format)
    non_Data_F.set_index("Tarih", inplace=True)
    non_Data_F = non_Data_F.resample('1D').sum()
    non_Data_F = non_Data_F[non_Data_F["Üretim Kaybı"] != 0]
    return non_Data_F
@st.experimental_memo
def loseDates():
    lose_dates = response.loc[response.Fark == 0]
    lose_dates = lose_dates[['Toplam-Üretim-(kW/h)','Fark']].between_time('08:30','18:00')
    lose_dates.reset_index(inplace=True)
    lose_dates.drop(columns=['Toplam-Üretim-(kW/h)','Fark',] ,inplace=True)
    lose_dates["Tarih"] = date_to_str(date=lose_dates["Tarih"], format=dateTime_format)
    lose_dates["Üretim Kaybı"] = lose_dates["Tarih"].str[11:16]
    responseLoses = response[response["Fark"] > 0]
    lose_dates["Üretim Kaybı"] = lose_dates["Üretim Kaybı"].apply(lambda x : responseLoses['Fark'].at_time(x).mean())
    lose_dates['Tarih'] = pd.to_datetime(lose_dates.Tarih, format=dateTime_format)
    lose_dates.set_index("Tarih", inplace=True)
    lose_dates = lose_dates.resample('1D').sum()
    lose_dates = lose_dates[lose_dates["Üretim Kaybı"] != 0]
    return lose_dates
@st.experimental_memo
def fetchInverterDetailsData(siteID):
    url = f"{base_url}/plant/{siteID}"
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {key}' }
    response = requests.request("GET", url, headers=headers,).json()
    print(type(response))
    response = pd.json_normalize(response,"devices")
    inverterDetails=response[["id","label","serial","latestData","isOffline"]]
    inverterDetailsDict = response[["id","label"]]
    #inverterDetails["lastConnection"] = datetime.datetime.fromtimestamp(inverterDetails["lastConnection"])
    return inverterDetails,inverterDetailsDict
@st.experimental_memo
def convert_to_int(value):
    if value.isdigit():
        value = int(value)
        return value
    else:
        return value
with st.form(key="Santral Seçim Forumu"):
    with  st.sidebar:
        selectedPlant= st.selectbox(
            "Santarli Seçiniz",
            ("Cactus Farm", "PUTAS Textil", "Yaylakoy","Cena Alasehir","Irmak Depoları","DOST Madencilik","Özçakım Mermer","Defne Çatı Ges","Hitit","ASP","Barlas Soğutma","Çağlacan","Cereyan","Chef Seasons","ELMAS Lojistik","Defne Ges-3","Defne Ges-4","Defne Ges-5","Defne Ges-6","Defne Ges-7","Defne Ges-8","Liva Grup ITOB","Kozağaç Karya","Kozağaç Medis","Özkaramanlar ")
        )
        
        siteID = get_key(val = selectedPlant)
        startDate = st.date_input(
            "Başlangıç Tarihi Giriniz",
            datetime.datetime.now(),
            max_value= datetime.datetime.now()
        )
        endDate = st.date_input(
            "Bitiş Tarihi Giriniz",
            datetime.datetime.now(),
            max_value= datetime.datetime.now()
        )
        is_it_daily = st.checkbox("GÜNLÜK")
        if is_it_daily:
            options_disabled = True
            aralik = 1
            freq = "1D"
            reactive_daily = True
        if is_it_daily==False and endDate - startDate > datetime.timedelta(days = 20):
            options_disabled = True
            is_it_daily = True
            aralik = 1
            freq = "1D"
            reactive_daily = True
        submit_button =  st.form_submit_button()
        if submit_button:
            st.experimental_memo.clear()

with st.sidebar:
    values = st.radio(
        'Aralık Seçiniz',
        options=["5DK", "15DK","30DK", "60DK",],disabled=options_disabled or is_it_daily)
    if values == "5DK":
        aralik = 1
        freq = "5T"
    elif values == "15DK":
        aralik = 3
        freq = "15T"
    elif values == "30DK":
        aralik = 6
        freq = "30T"
    elif values == "60DK":
        aralik = 12
        freq = "1H"
    if reactive_daily:
        reactive_display = st.checkbox("Reaktif")
if endDate < startDate:
    with st.sidebar:
        st.error('Bitiş Tarihi Başlangıç Tarihinden Önce Olamaz.')
        st.stop()
reverse_date = st.sidebar.checkbox('Yeniden Eskiye Doğru Sırala')
if reverse_date:
    reverse_bool = False
else:
    reverse_bool= True

key = login ()
days_between = endDate - startDate

lottie_url_dataflow="https://assets9.lottiefiles.com/packages/lf20_mhw15oyy.json"
lottie_dataflow = load_lottieurl(lottie_url_dataflow)
lottie_url_notFound="https://assets8.lottiefiles.com/packages/lf20_cr9slsdh.json"
lottie_notFound = load_lottieurl(lottie_url_notFound)
lottie_url_graph = "https://assets2.lottiefiles.com/packages/lf20_lwt53pag.json"    
lottie_graph= load_lottieurl(lottie_url_graph)
lottie_url_grid = "https://assets8.lottiefiles.com/packages/lf20_ge7s4cgp.json"
lottie_grid = load_lottieurl(lottie_url_grid)
lottie_url_404 = "https://assets8.lottiefiles.com/packages/lf20_6nmazhqu.json"
lottie_404 = load_lottieurl(lottie_url_404)
lottie_url_hamster = "https://assets3.lottiefiles.com/packages/lf20_jk2naj.json"
lottie_hamster = load_lottieurl(lottie_url_hamster)
lottie_url_sun = "https://assets9.lottiefiles.com/private_files/lf30_zbomp8ks.json"
lottie_sun = load_lottieurl(lottie_url_sun)

file_name_Yield = f"{selectedPlant} {startDate}-{endDate}.xlsx"
file_name_Power = f"P_{selectedPlant} {startDate}-{endDate}.xlsx"   #indirme butonu başlıyor

try:
    inverterDetails= fetchInverterDetailsData(siteID)[0]
    inverterDetailsDict = fetchInverterDetailsData(siteID)[1]
    inverterDetailsDict= inverterDetailsDict.set_index("id").to_dict()
    inverterDetailsObtained= True
except: 
    inverterDetailsObtained= False
    pass
try:
    #response = fetchData(siteID=siteID,startDate=startDate,endDate=endDate, daily= is_it_daily)
    response = fetchData(siteID, startDate, endDate, is_it_daily)
    response = dataOrginizer(response=response,aralik=aralik,reverse_bool=reverse_bool)
    if inverterDetailsObtained:
        response.rename(columns=lambda x: inverterDetailsDict["label"][convert_to_int(x)] if convert_to_int(x) in inverterDetailsDict["label"] else x, inplace=True)
        response.columns = response.columns.str.replace(' ', '')

except :
    st.error("Data Alınamadı..")
    colx,coly,colz = st.columns(3)
    with coly:
        st_lottie(lottie_notFound, key="notFound"  , quality= "high",)
    st.stop()
try:
    if is_it_daily == False and days_between < datetime.timedelta(days=2):
        ac_data = fetch_AC_Data(siteID,startDate,endDate,)[0]
        if inverterDetailsObtained:
            ac_data.rename(columns=lambda x: inverterDetailsDict["label"][convert_to_int(x)] if convert_to_int(x) in inverterDetailsDict["label"] else x, inplace=True)
            
            ac_data.columns = ac_data.columns.str.replace(' ', '')
        ac_data_obtained = True
    else :
        ac_data_obtained = False
except :
    pass
if ac_data_obtained:
    ac_grouped_mppt = ac_data_orginizer()[0]
    ac_grouped_zero = ac_data_orginizer()[1]

 
chart = response.copy().reset_index()
chart_data = chart[['Tarih','Toplam-Üretim-(kW/h)']]
heat_data = chart[['Tarih','Fark']]
heat_data = heat_data[heat_data["Fark"].between(0,150) ]
line_chart = chart.copy()
line_chart.drop(["Toplam-Üretim-(kW/h)"], axis = 1, inplace=True)
fig_yield = px.area(chart_data, x="Tarih", y = "Toplam-Üretim-(kW/h)",title=f'{selectedPlant} Yield', )
if is_it_daily:
    chart_data["Tarih"] = date_to_str(date = chart_data["Tarih"], format = dateTime_format )
        #chart_data["Tarih"] = chart_data["Tarih"].dt.strftime("%Y-%m-%d %H:%M:%S")
    chart_data["Tarih"] = dateTime_to_Date(chart_data["Tarih"])
    bar_daily_fig = px.bar(chart_data, x='Tarih', y='Toplam-Üretim-(kW/h)',
                color='Toplam-Üretim-(kW/h)',
                height=400)
    pie_chart = px.pie(chart_data, values='Toplam-Üretim-(kW/h)', names='Tarih' , title="Günlük Üretim Değerleri Dağılımı" , ) 
    pie_chart.update_layout(  margin=dict(
            l=20,
            r=20,
            b=50,
            t=50,
            pad=4
        ),)
        #chart_data["Tarih"] = chart_data["Tarih"].str[:10]
else: 
    heat_data["Tarih"]  = heat_data["Tarih"].dt.strftime('%H:%M')
    heat_fig = px.scatter(heat_data, x="Tarih", y="Fark",size_max=60, title="Saatlik Üretim Dağılımı", color="Fark")
    fig_yield.update_layout(  margin=dict(
            l=50,
            r=30,
            b=100,
            t=80,
            pad=4
        ),)
    #st.line_chart(chart_data)
line_fig = px.line(line_chart, x = "Tarih", y =line_chart.columns.difference(['Tarih','Fark']), title= f"{selectedPlant} Inverter Bazında Yield")
line_fig.update_layout(  margin=dict(
            l=50,
            r=30,
            b=100,
            t=80,
            pad=4
        ),)

try:
        #reactive = fetchReactiveData(siteID=siteID,startDate=startDate,endDate=endDate)
        #reactive = asyncio.create_task(fetchReactiveData(siteID,startDate,endDate)) 
    if not is_it_daily:
        reactive = fetchReactiveData(siteID,startDate,endDate)
        line_fig_Reactive = px.line(reactive, x = "timestamp", y =reactive.columns.difference(['timestamp']), title= f"{selectedPlant} CosPhi Değerleri")
        line_fig_Reactive.update_layout(  margin=dict(
                        l=50,
                        r=0,
                        b=100,
                        t=80,
                        pad=4
                    ),)
except :
    pass

color_table = response.copy().reset_index()
color_table["Tarih"] = date_to_str(date =color_table["Tarih"] , format= dateTime_format )
#color_table["Tarih"] = color_table["Tarih"].dt.strftime("%Y-%m-%d %H:%M:%S")

if is_it_daily:
    color_table["Tarih"] = dateTime_to_Date(color_table["Tarih"])
    #color_table["Tarih"] = color_table["Tarih"].str[:10]
color_table['total'] = color_table['Toplam-Üretim-(kW/h)'].sum()
uretim_data = color_table['total'][0].round(3)
st.title(selectedPlant)
non_Data_F_calculated=False
non_Data_F = nonDataDates()
non_Data_F_calculated = True

lose_dates = loseDates()

if not is_it_daily: #5dk lık datalar için oluşuturulan layout
    col1 , col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_yield,use_container_width=True)
    with col2:
        st.plotly_chart(line_fig,use_container_width=True )
    col3, col4 = st.columns(2)
    with col3:
        try:
            st.plotly_chart(line_fig_Reactive,use_container_width=True )
        except :
            st.info("Reaktif Güç Değerleri Mecvut Değil.")
            st_lottie(lottie_404, key="404" , height=400 , width=800 , quality= "high",)
    with  col4:
        st.plotly_chart(heat_fig,use_container_width=True )
    if ac_data_obtained:
        inverter_fig(ac_data)
        file_name_MPPT = f"MPPT-{selectedPlant}-{startDate}, {endDate}.xlsx"
        with st.expander(label="MPPT Değeleri"):
            if ac_grouped_mppt.empty: 
                st.info("MPPT Değerleri Arasında Kayda Değer Bir Fark Tespit Edilemedi.")
                colx, coly, colz = st.columns(3)
                with coly:
                    st_lottie(lottie_graph, key="graph" , height=200 , quality= "high",)
            else:
                st.table(ac_grouped_mppt)
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    ac_grouped_mppt.to_excel(writer, sheet_name=f"MPPT-{selectedPlant}-{startDate}")
                    writer.save()
                    st.download_button(
                            label="Download Excel worksheets",
                            data=buffer,
                            file_name=file_name_MPPT,
                            mime="application/vnd.ms-excel"
                        )
        with st.expander(label="Üretim Yapmayan İnverterler"):
            if ac_grouped_zero.empty:
                st.info("Seçilen Aralıkta Tüm Inverterler Üretimde")
                colx,coly,colz = st.columns(3)
                with coly:
                    st_lottie(lottie_hamster, key="hamster" , height=200 , quality= "high",)
            else:
                st.table(ac_grouped_zero)
        with st.expander(label="Güç Değerleri"):
            st.write(ac_data)
            
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                ac_data.to_excel(writer, sheet_name=f"AC-{selectedPlant}-{startDate}")
                writer.save()
                st.download_button(
                    label="Download Power Data",
                    data=buffer,
                    file_name=file_name_Power,
                    mime="application/vnd.ms-excel",
                   
                )
        if inverterDetailsObtained:
            with st.expander("İnverter Detayları"):
                st.table(fetchInverterDetailsData(siteID)[0])      
    if days_between > datetime.timedelta(days=1):
        with st.expander(label="Şebeke Kayıplarını Görüntüle"):
            if lose_dates.empty:
                st.info("Seçilen Aralıkta Kayıp Tespit Edilememiştir.")
                colx,coly,colz = st.columns(3)
                with coly:
                    st_lottie(lottie_grid, key="grid" , height=200 , quality= "high",)
            else:
                lose_dates.reset_index(inplace=True)
                 #lose_dates["Tarih"] = date_to_str(date = lose_dates["Tarih"] ,format=dateTime_format)
                #lose_dates["Tarih"] = lose_dates["Tarih"].dt.strftime("%Y-%m-%d %H:%M:%S")
                 #lose_dates["Tarih"] = dateTime_to_Date(lose_dates["Tarih"])
                #lose_dates["Tarih"] = lose_dates["Tarih"].str[:10]
                st.table(lose_dates)
    if non_Data_F_calculated:
        with st.expander(label="Data Alınamayan Tarihleri Görüntüle"):
            if non_Data_F.empty:
                st.info("Seçilen Aralıkta Data Akışı Stabildir.")
                colx,coly,colz = st.columns(3)
                with coly:
                    st_lottie(lottie_dataflow, key="dataflow", height=200  , quality= "high",)
                #st_lottie(lottie_grid, key="grid" , height=200 , width=1500 , quality= "high",)
            else:
                non_Data_F.reset_index(inplace=True)
                #non_Data_F["Tarih"] = date_to_str(date = non_Data_F["Tarih"] ,format=dateTime_format)
                #non_Data_F["Tarih"] = dateTime_to_Date(non_Data_F["Tarih"])
                st.table(non_Data_F) 
    try:  
        allLoses = pd.concat([lose_dates, non_Data_F] , sort=True)
        allLoses.set_index("Tarih", inplace=True)
        allLoses.sort_index(inplace=True)
        try:
            allLoses["Üretim Kaybı"]=allLoses["Üretim Kaybı"].round(2)
        except :
                pass
        allLoses.reset_index(inplace=True)
        allLoses["Tarih"] = date_to_str(date = allLoses["Tarih"] ,format=dateTime_format)
        allLoses["Tarih"] = dateTime_to_Date(allLoses["Tarih"])
        allLoses.set_index("Tarih", inplace=True)
        print(type(allLoses))
        
        with pd.ExcelWriter(buffer_Z, engine='xlsxwriter') as writer:
            allLoses.to_excel(writer, sheet_name=f"{selectedPlant}-Şebeke Kayıpları")
            writer.save()
            st.download_button(
                            label="Download Lose Days Data",
                            data=buffer_Z,
                            file_name=f"{selectedPlant}-Şebeke Kayıpları.xlsx",
                            mime="application/vnd.ms-excel"
                        )
    except :
        pass #indrime butonu bitiyor   
else: #günlük datalar için oluşturulan layout
    st.metric(label="Toplam Üretim", value=f"{uretim_data} kWh",)
    st.markdown('#')
    colx, coly = st.columns(2)
    with colx:
        st.plotly_chart(line_fig,use_container_width=True )
    with coly:
        st.plotly_chart(pie_chart,use_container_width=True )

    st.plotly_chart(bar_daily_fig ,use_container_width=True)
    if reactive_display:
        try:
            reactive = fetchReactiveData(siteID,startDate,endDate)
            line_fig_Reactive = px.line(reactive, x = "timestamp", y =reactive.columns.difference(['timestamp']), title= f"{selectedPlant} CosPhi Değerleri")
            line_fig_Reactive.update_layout(  margin=dict(
                            l=50,
                            r=0,
                            b=100,
                            t=80,
                            pad=4
                        ),)
            st.plotly_chart(line_fig_Reactive,use_container_width=True )
        except :
            st.info("Reaktif Güç Değerleri Mecvut Değil.")
            colx,coly,colz = st.columns(3)
            with coly:
                st_lottie(lottie_404, key="404" , height=400 , quality= "high",)
#2. threadi beklemediği için sürekli mevcut değile deüşüyor. grafiğin fonksiyonunu da joinden sonra çağırabilirim ama future ile yapmak daha mantıklı olur gibi

#ag = AgGrid(color_table ,theme='streamlit', allow_unsafe_jscode=True)
#color_table = color_table.style.hide_index()
yield_sheet_Name = f"Y-{selectedPlant}-{startDate}"
with st.expander("Üretim Değerleri"): #üretim dataları tablosu
    st.dataframe(color_table.drop("total", axis=1))
    if not response.empty:
        with pd.ExcelWriter(buffer_Y, engine='xlsxwriter') as writer:
            response.to_excel(writer, sheet_name=yield_sheet_Name)
            writer.save()
            st.download_button(
                label="Download Yield Data",
                data=buffer_Y,
                file_name=file_name_Yield,
                mime="application/vnd.ms-excel"
            ) #indrime butonu bitiyor



#color_table.rename(columns=lambda x: inverterDetailsDict["label"][convert_to_int(x)] if convert_to_int(x) in inverterDetailsDict["label"] else x, inplace=True)
#color_table.columns = color_table.columns.str.replace(' ', '')

#st_lottie(lottie_url_graph, key="graph" , height=400 , width=400,  quality= "high" )
#print(days_between)
#ac_grouped = ac_data_orginizer()[2]
#st.write(ac_grouped)

#ac_grouped = ac_grouped.groupby(["timestamp","id", "index",]).mean()
#ac_grouped["p"]=ac_grouped["p"].round(3)
#ac_grouped['Fark'] = ac_grouped.groupby(["index", "p" ]).pct_change()
#ac_grouped = ac_grouped.asfreq('30T')
#response.set_index("timestamp", inplace=True)
#ac_grouped = ac_grouped.between_time("07:30" , "19:00")

#inverters_list = ac_data[ac_data.columns.values.tolist()]
