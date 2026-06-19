"""TaskMe — núcleo determinístico de gestão/cobrança de tarefas.

Toda a lógica de negócio (validação, datas, máquina de estados, fila,
templates e consultas) vive aqui. O plugin Hermes e os cron jobs são
adaptadores finos que importam este pacote.
"""

__version__ = "0.1.0"
