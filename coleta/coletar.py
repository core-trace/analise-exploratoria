"""Salva as métricas reais em CSV, sem API, banco ou envio ao bucket."""
import argparse
import csv
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "coretrace"))
from cpu.coleta import IDS_CPU, preparar_coleta_cpu, colunas_cpu, coletar_cpu
from ram.coleta import IDS_RAM, preparar_coleta_ram, colunas_ram, coletar_ram
from swap.coleta import IDS_SWAP, preparar_coleta_swap, colunas_swap, coletar_swap
from carga.coleta import IDS_CARGA, preparar_coleta_carga, colunas_carga, coletar_carga
from disco.coleta import IDS_DISCO, preparar_coleta_disco, colunas_disco, coletar_disco_geral
from rede.coleta import IDS_REDE, preparar_coleta_rede, colunas_rede, coletar_rede_geral


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--cenario", choices=["basico", "cpu", "memoria", "disco", "recuperacao"], default="basico")
    argumentos.add_argument("--duracao", type=int, default=300, help="Duração em segundos; padrão: 300 (5 minutos).")
    argumentos.add_argument("--intervalo", type=float, default=1, help="Pausa entre leituras, em segundos.")
    argumentos.add_argument("--saida", type=Path, default=Path(__file__).parents[1] / "dados" / "brutos")
    opcoes = argumentos.parse_args()
    if opcoes.duracao <= 0 or not 0.1 <= opcoes.intervalo <= 60:
        argumentos.error("Use duração positiva e intervalo entre 0,1 e 60 segundos.")

    
    cpu = preparar_coleta_cpu(IDS_CPU)
    ram = preparar_coleta_ram(IDS_RAM)
    swap = preparar_coleta_swap(IDS_SWAP)
    carga = preparar_coleta_carga(IDS_CARGA)
    disco = preparar_coleta_disco(IDS_DISCO)
    rede = preparar_coleta_rede(IDS_REDE)

    colunas = ["TIMESTAMP", "ENDERECO_MAC", "CENARIO", "EXPERIMENTO", "TEMPO_SEGUNDOS"]
    colunas += colunas_cpu(cpu) + colunas_ram(ram) + colunas_swap(swap)
    colunas += colunas_carga(carga) + colunas_disco(disco) + colunas_rede(rede)
    
    colunas = list(dict.fromkeys(colunas))

    mac = "-".join(f"{uuid.getnode():012X}"[i:i + 2] for i in range(0, 12, 2))
    experimento = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    opcoes.saida.mkdir(parents=True, exist_ok=True)
    caminho = opcoes.saida / f"coretrace_{opcoes.cenario}_{experimento}.csv"
    inicio = time.monotonic()
    quantidade = 0

    
    with caminho.open("x", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        print(f"Coletando cenário {opcoes.cenario}. Nenhuma carga é iniciada por este script.")
        try:
            while time.monotonic() - inicio < opcoes.duracao:
                horario = datetime.now().isoformat(timespec="milliseconds")
                segundos = time.monotonic() - inicio
                dados = {}
                dados.update(coletar_cpu(cpu))
                dados.update(coletar_ram(ram))
                dados.update(coletar_swap(swap))
                dados.update(coletar_carga(carga))
                dados.update(coletar_disco_geral(disco))
                dados.update(coletar_rede_geral(rede))
                dados.update(TIMESTAMP=horario, ENDERECO_MAC=mac,
                             CENARIO=opcoes.cenario, EXPERIMENTO=experimento,
                             TEMPO_SEGUNDOS=round(segundos, 3))
                escritor.writerow(dados)
                arquivo.flush()
                quantidade += 1
                restante = opcoes.duracao - (time.monotonic() - inicio)
                if restante > 0:
                    time.sleep(min(opcoes.intervalo, restante))
        except KeyboardInterrupt:
            print("Coleta interrompida por você.")
    print(f"{quantidade} leituras salvas em: {caminho}")


if __name__ == "__main__":
    main()
