from fastapi import FastAPI
import datetime
import requests
import logging
from bs4 import BeautifulSoup
from unidecode import unidecode
from babel.dates import format_date
from pydantic import BaseModel

BASE_URL = "https://liguesaintamedee.ch/"

class Saint(BaseModel):
    nom: str
    description: str
    image: str | None = None

app = FastAPI(title="API Saint du Jour")

# Configuration du logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="saint_du_jour.log"
)

def recuperer_page_saints_du_mois(nom_du_mois) -> BeautifulSoup:
    # Construction de l'URL permettant de récuperer les Saints du mois
    url = f"{BASE_URL}saints-{unidecode(nom_du_mois)}.html"

    # Récupération de la page des Saints du mois
    reponse = requests.get(url, verify=False)

    if not reponse.ok:
        raise RuntimeError(f"Erreur HTTP {reponse.status_code} en récupérant {url}")

    return BeautifulSoup(reponse.content, "html.parser")

def recuperer_url_image_saint_du_jour(page_web, nom_saint) -> str:
    return page_web.find(alt=nom_saint, name="img")

@app.get("/")
async def recuperer_saints_du_jour(jour: datetime.date | None = None) -> list[Saint]:

    if jour is None:
        jour = datetime.date.today()

    logger.info('Lancement de la récupération des Saints du jour')

    saints_du_jour = []

    nom_du_mois = format_date(jour, format="MMMM", locale="fr_FR")
    
    try:
        html_parse = recuperer_page_saints_du_mois(nom_du_mois)
    except Exception as e:
        logger.error(f"Impossible de récupérer la page des saints : {e}")
        return []  # le script continue, mais vide

    numero_jour = '{dt.day}'.format(dt = jour)
    if numero_jour == "1":
        numero_jour = "1er"

    resultats_recherche_balises_saint = html_parse.find_all(string = f"{numero_jour} {nom_du_mois}", name="b")
    
    # Je parcours l'ensembe des balises
    for balise_saint in resultats_recherche_balises_saint:

        # Récupération de la date de ce Saint
        date_saint = balise_saint.contents[0]

        nom_saint = None
        description_saint = ""

        for element_html in date_saint.next_elements:
            element_texte = element_html.text

            # Si on arrive sur le texte " Retour en haut ", c'est qu'on a finit de lire la description de ce saint, on peut passer au suivant
            if element_texte.strip() == "Retour en haut":
                break
            if element_texte.strip() != '':
                if element_html.name == "u":
                    nom_saint = element_html.text
                    logger.info(f"Saint récupéré : {nom_saint}")
                elif element_html.name != "i":
                    description_saint += element_texte

        saint_du_jour = Saint(nom=nom_saint, description=description_saint)

        # Recherche de l'image du Saint
        image = recuperer_url_image_saint_du_jour(html_parse, nom_saint)

        # Si elle existe ...
        if image:

            # L'ajouter au sein du jour
            saint_du_jour.image = BASE_URL + image.attrs['src']

        saints_du_jour.append(saint_du_jour)

    logger.info(f"Récupération des Saints du jour terminé : {len(saints_du_jour)} récupéré(s)")
    return saints_du_jour