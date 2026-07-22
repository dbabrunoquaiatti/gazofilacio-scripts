import sys
import os

if sys.platform == "win32":
    PASTA_IMAGENS = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral\dados"
    JSON_PESSOAS  = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral\dados\pessoas.json"
    CSV_PESSOAS   = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral\dados\pessoas.csv"
else:
    PASTA_IMAGENS = "/home/node/data/"
    JSON_PESSOAS  = "/home/node/data/pessoas.json"
    CSV_PESSOAS   = "/home/node/data/pessoas.csv"

PASTA_INST = os.path.join(PASTA_IMAGENS, "inst")
