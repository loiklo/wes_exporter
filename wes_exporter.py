#!/usr/bin/python3
"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge, Counter, Enum
import requests
import xmltodict
import re
import pprint

re_pceval_amps = re.compile("<value>([0-9.]*) A</value>")
re_pceval_watts_cosphi = re.compile("<value>([0-9.]*) W cos phi ([0-9.]*)</value>")
re_pceval_kwh = re.compile("<value>([0-9.]*) kWh</value>")

tic_ptec_options = ["H. Creuse BLEU", "H. Pleine BLEU", "H. Creuse BLANC", "H. Pleine BLANC", "H. Creuse ROUGE", "H. Pleine ROUGE", "Inconnu", "H. Creuses", "H. Pleines"]
tic_demain_options = ["Jour BLEU", "Jour BLANC", "Jour ROUGE", "Inconnu"]

class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, app_port=80, polling_interval_seconds=5):
        self.app_port = app_port
        self.polling_interval_seconds = polling_interval_seconds

        # Prometheus metrics to collect
        self.tic_ptec   = Enum("wes_tic_ptec", "Couleur actuelle", states=tic_ptec_options)
        self.tic_demain = Enum("wes_tic_demain", "Couleur demain", states=tic_demain_options)

        self.tic_ptec_num = Gauge("wes_tic_ptec_num", "Couleur actuelle numerique")
        self.tic_demain_num = Gauge("wes_tic_demain_num", "Couleur demain numerique")


        self.tic_isoucs = Gauge("wes_tic_isoucs", "Intensite souscrite", ["id"])
        self.tic_pap    = Gauge("wes_tic_pap", "Puissance apparente", ["id"])
        self.tic_iinst  = Gauge("wes_tic_iinst", "Intensite instantanee", ["id"])
        self.tic_index  = Counter("wes_tic_index", "Index", ["id", "option", "color", "phase"])

        self.impulsion_index = Counter("wes_impulsion_index", "Index impulsion", ["id"])

        self.pince_i      = Gauge("wes_pince_i", "Intensite instantanee", ["id"])
        self.pince_index  = Counter("wes_pince_index", "Index pince", ["id"])
        self.pince_amps   = Gauge("wes_pince_amps", "Ampere instantanee", ["id"])
        self.pince_watts  = Gauge("wes_pince_watts", "Puissance instantanee", ["id"])
        self.pince_cosphi = Gauge("wes_pince_cosphi", "Cos Phi", ["id"])
        self.pince_kwh    = Counter("wes_pince_kwh", "kWh total", ["id"])


        self.v = Gauge("wes_v", "Tension secteur")

    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        # Fetch raw status data from the application
        #resp = requests.get(url=f"http://localhost:{self.app_port}/status")
        resp_data_xml = requests.get(url=f"http://admin:wes@wes.bty.loiklo.net/DATA.CGX")
        resp_pceval_html = requests.get(url=f"http://admin:wes@wes.bty.loiklo.net/WEBPROG/CGX/PCEVAL.CGX")
        resp_data = xmltodict.parse(resp_data_xml.content)

        #print(resp_pceval_html.content.decode())
        pceval_amps = re_pceval_amps.findall(resp_pceval_html.content.decode())
        pceval_watts_cosphi = re_pceval_watts_cosphi.findall(resp_pceval_html.content.decode())
        pceval_kwh = re_pceval_kwh.findall(resp_pceval_html.content.decode())

        for i in range(1,3):
          self.tic_isoucs.labels(id=i).set(resp_data["data"][f"tic{i}"]["ISOUSC"])
          self.tic_pap.labels(id=i).set(resp_data["data"][f"tic{i}"]["PAP"])
          self.tic_iinst.labels(id=i).set(resp_data["data"][f"tic{i}"]["IINST"])
          if "BASE" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="base",  color="none",  phase="none")._value.set(resp_data["data"][f"tic{i}"]["BASE"])
          if "BBRHCJB" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="tempo", color="blue",  phase="hc")._value.set(resp_data["data"][f"tic{i}"]["BBRHCJB"])
          if "BBRHPJB" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="tempo", color="blue",  phase="hp")._value.set(resp_data["data"][f"tic{i}"]["BBRHPJB"])
          if "BBRHCJW" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="tempo", color="white", phase="hc")._value.set(resp_data["data"][f"tic{i}"]["BBRHCJW"])
          if "BBRHPJW" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="tempo", color="white", phase="hp")._value.set(resp_data["data"][f"tic{i}"]["BBRHPJW"])
          if "BBRHCJR" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="tempo", color="red",   phase="hc")._value.set(resp_data["data"][f"tic{i}"]["BBRHCJR"])
          if "BBRHPJR" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="tempo", color="red",   phase="hp")._value.set(resp_data["data"][f"tic{i}"]["BBRHPJR"])
          if "H_PLEINE" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="hphc", color="none",   phase="hp")._value.set(resp_data["data"][f"tic{i}"]["H_PLEINE"])
          if "H_CREUSE" in resp_data["data"][f"tic{i}"]:
            self.tic_index.labels(id=i, option="hphc", color="none",   phase="hc")._value.set(resp_data["data"][f"tic{i}"]["H_CREUSE"])

        # Entree a impulsion
        for i in range(1,5):
          self.impulsion_index.labels(id=i)._value.set(resp_data["data"]["impulsion"][f"INDEX{i}"])

        # Pinces amperemetriques
        for i in range(1,5):
          self.pince_i.labels(id=i).set(resp_data["data"]["pince"][f"I{i}"])
          self.pince_index.labels(id=i)._value.set(resp_data["data"]["pince"][f"INDEX{i}"])
          self.pince_amps.labels(id=i).set(pceval_amps[i-1])
          self.pince_watts.labels(id=i).set(pceval_watts_cosphi[i-1][0])
          self.pince_cosphi.labels(id=i).set(pceval_watts_cosphi[i-1][1])
          self.pince_kwh.labels(id=i)._value.set(pceval_kwh[i-1])

        self.v.set(resp_data["data"]["tic1"]["TENSION1"])

        if resp_data["data"]["tic1"]["PTEC"] in tic_ptec_options:
          self.tic_ptec.state(resp_data["data"]["tic1"]["PTEC"])
          match resp_data["data"]["tic1"]["PTEC"]:
            case "H. Creuse BLEU":
              self.tic_ptec_num.set(0)
            case "H. Pleine BLEU":
              self.tic_ptec_num.set(1)
            case "H. Creuse BLANC":
              self.tic_ptec_num.set(2)
            case "H. Pleine BLANC":
              self.tic_ptec_num.set(3)
            case "H. Creuse ROUGE":
              self.tic_ptec_num.set(4)
            case "H. Pleine ROUGE":
              self.tic_ptec_num.set(5)
            case "H. Creuses":
              self.tic_ptec_num.set(6)
            case "H. Pleines":
              self.tic_ptec_num.set(7)
        else:
          self.tic_ptec.state("Inconnu")
          self.tic_ptec_num.set(-1)

        if resp_data["data"]["tic1"]["DEMAIN"] in tic_demain_options:
          self.tic_demain.state(resp_data["data"]["tic1"]["DEMAIN"])
          match resp_data["data"]["tic1"]["DEMAIN"]:
            case "Jour BLEU":
              self.tic_demain_num.set(0)
            case "Jour BLANC":
              self.tic_demain_num.set(1)
            case "Jour ROUGE":
              self.tic_demain_num.set(2)
        else:
          self.tic_demain.state("Inconnu")
          self.tic_demain_num.set(-1)

        # Update Prometheus metrics with application metrics
        #self.current_requests.set(status_data["current_requests"])
        #self.pending_requests.set(status_data["pending_requests"])
        #self.total_uptime.set(status_data["total_uptime"])
        #self.health.state(status_data["health"])

def main():
    """Main entry point"""

    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "3"))
    app_port = int(os.getenv("APP_PORT", "80"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    app_metrics = AppMetrics(
        app_port=app_port,
        polling_interval_seconds=polling_interval_seconds
    )
    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()

if __name__ == "__main__":
    main()
