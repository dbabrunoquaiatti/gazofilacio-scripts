import sys
import os

if sys.platform == "win32":
    PASTA_IMAGENS = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral\dados"
else:
    PASTA_IMAGENS = "/home/node/data/"

PASTA_INST = os.path.join(PASTA_IMAGENS, "inst")
