#!/usr/bin/env python
import os

def deloldfile():
    path = 'D:\\Projects\\deployment\\autojar\\static\\upload\\'
    for i in os.listdir(path):
        os.remove(path+i)




