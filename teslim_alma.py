import streamlit as st
import pandas as pd
from datetime import datetime

def run(conn):

    st.title("Mal Kabul")

    kod = st.text_input("Kod", key="teslim_alma_kod")
    isim = st.text_input("İsim", key="teslim_alma_isim")
    miktar = st.number_input("Miktar", 0.0, key="teslim_alma_miktar")
    tedarikci = st.text_input("Tedarikçi", key="teslim_alma_tedarikci")

    if st.button("Giriş Yap", key="teslim_alma_btn"):
        try:
            # GSheets mevcut veriyi çek
            try:
                hareketler_df = conn.read(worksheet="Hareketler", ttl="0")
            except:
                hareketler_df = pd.DataFrame(columns=["Tarih", "Kod", "İsim", "Miktar", "Tedarikçi"])
            
            # Yeni kaydı DataFrame olarak oluştur
            yeni_kayit = pd.DataFrame([{
                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Kod": kod,
                "İsim": isim,
                "Miktar": miktar,
                "Tedarikçi": tedarikci
            }])
            
            # Append wrapper hatasını ekarte etmek için concat + update
            guncel_df = pd.concat([hareketler_df, yeni_kayit], ignore_index=True)
            conn.update(worksheet="Hareketler", data=guncel_df)
            
            st.success("Başarılı")
        except Exception as e:
            st.error(str(e))
