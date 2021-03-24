#  qmake project file for the kva2json example (part of GEMS3K standalone code)
# (c) 2020 GEMS Developer Team
 
TEMPLATE = app
LANGUAGE = C++
TARGET = kva2json
VERSION = 3.4.6

CONFIG -= qt
CONFIG -= warn_on
CONFIG += debug
CONFIG += console
CONFIG += c++17


DEFINES += IPMGEMPLUGIN
DEFINES += NODEARRAYLEVEL
DEFINES += NOPARTICLEARRAY

!win32 {

DEFINES += __unix
QMAKE_CFLAGS += pedantic -Wall -Wextra -Wwrite-strings -Werror

QMAKE_CXXFLAGS += -Wall -Wextra -Wformat-nonliteral -Wcast-align -Wpointer-arith \
 -Wmissing-declarations -Winline \ # -Wundef \ #-Weffc++ \
 -Wcast-qual -Wshadow -Wwrite-strings -Wno-unused-parameter \
 -Wfloat-equal -pedantic -ansi

}

GEMS3K_CPP = ../GEMS3K
GEMS3K_H   = $$GEMS3K_CPP

DEPENDPATH += .
DEPENDPATH += $$GEMS3K_H

INCLUDEPATH += .
INCLUDEPATH += $$GEMS3K_H


QMAKE_LFLAGS +=
QMAKE_CXXFLAGS += -Wall -Wno-unused
OBJECTS_DIR = obj

include($$GEMS3K_CPP/gems3k.pri) 

HEADERS   +=   args_tool.h
SOURCES   +=   kva2json.cpp

