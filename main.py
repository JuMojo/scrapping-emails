import re
from io import BytesIO

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from fp.fp import FreeProxy

# SCRAPPER SCRIPT
proxy = FreeProxy(country_id=['GB', 'US', 'BR']).get()


def request_website(website):
    try:
        response = requests.get(website, proxies={"http": proxy})

        if response.status_code == 200:
            # Initialisation de BeautifulSoup avec le contenu de la réponse
            soup = BeautifulSoup(response.content, "html.parser")

            # Recherche de tous les liens dans la page
            links = [link.get("href") for link in soup.find_all("a", href=True)]
            valid_links = [link for link in links if
                           not link.endswith((".aspx", ".pdf", ".mp4")) and link.startswith(("/", "http"))]
            contacts_links = [link for link in valid_links if any(word in link for word in ['contact', 'mention'])]
            return contacts_links
    except:
        pass


def scrape_emails(links, base_url):
    email_list = []

    try:
        for link in links:
            print(link)
            # Si le lien ne commence pas par "http" ou "https", ajouter la base URL
            if not link.startswith("http"):
                link = base_url[:-1] + link

            response = requests.get(link, proxies={"http": proxy})

            # Vérification du statut de la réponse pour s'assurer que la requête a réussi
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", soup.text)
                valid_emails = [x for x in emails if x.endswith((".com", ".fr"))]
                if valid_emails:
                    email_list.append(valid_emails)
        flattened_email_list = [item for sublist in email_list for item in sublist]
        if flattened_email_list:
            print(flattened_email_list)
            extensions = [email.split("@")[1] for email in flattened_email_list]
            return set(flattened_email_list), set(extensions)
        else:
            return "", ""
    except:
        return "", ""


def set_email(website):
    links = request_website(website)
    print(links)
    emails, extensions = scrape_emails(links, website)
    return pd.Series([emails, extensions])


# STREAMLIT APP
def to_excel(df: pd.DataFrame):
    in_memory_fp = BytesIO()
    df.to_excel(in_memory_fp, index=False)
    in_memory_fp.seek(0, 0)
    return in_memory_fp.read()


st.title("Scrapping de site web")
st.markdown("---")

st.info(
    """
    Nom de colonnes exacte à inclure **obligatoirement** :
    - website
    - nom
    - prenom
    """, icon="ℹ️")

contacts = st.file_uploader("Inserez le fichier à scrapper")

if contacts:
    df = pd.read_csv(contacts)[:40]
    df.dropna(subset=["company_website"], inplace=True)
    df["company_website"] = np.where(df["company_website"].str.endswith("/"), df["company_website"],
                                     df["company_website"] + "/")

    df[["emails", "extension"]] = df["company_website"].apply(set_email)
    excel_data = to_excel(df)
    file_name = "scrapping_email.xlsx"
    st.dataframe(df)
    st.download_button("Télécharger le fichier", excel_data, file_name, f'text/{file_name}')
