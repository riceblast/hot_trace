CC = gcc
CXX = g++
CFLAGS = -Wall -O2 -g
#CXXFLAGS = -Wall -O2 -g
CXXFLAGS = -Wall -g

#SRCDIR = src
#OBJDIR = obj
BINDIR = bin
#
#SRC = $(wildcard $(SRCDIR)/*.c $(SRCDIR)/*.cpp)
#OBJ = $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(filter %.c,$(SRC))) \\
#      $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(filter %.cpp,$(SRC)))
#BIN = $(BINDIR)/myapp

ideal_global_distribution: ideal_global_distribution.cpp
		mkdir -p ${BINDIR}
		$(CXX) $(CXXFLAGS) -o ${BINDIR}/$@ $^

ideal_hot_distribution: ideal_hot_distribution.cpp
		mkdir -p ${BINDIR}
		$(CXX) $(CXXFLAGS) -o ${BINDIR}/$@ $^

#$(BIN): $(OBJ)
#    $(CXX) $(CXXFLAGS) -o $@ $^
#
#$(OBJDIR)/%.o: $(SRCDIR)/%.c
#    $(CC) $(CFLAGS) -c -o $@ $<
#
#$(OBJDIR)/%.o: $(SRCDIR)/%.cpp
#    $(CXX) $(CXXFLAGS) -c -o $@ $<
#SRCDIR = src
#OBJDIR = obj
#BINDIR = bin
#
#SRC = $(wildcard $(SRCDIR)/*.c $(SRCDIR)/*.cpp)
#OBJ = $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(filter %.c,$(SRC))) \\
#      $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(filter %.cpp,$(SRC)))
#BIN = $(BINDIR)/myapp
#
#$(BIN): $(OBJ)
#    $(CXX) $(CXXFLAGS) -o $@ $^
#
#$(OBJDIR)/%.o: $(SRCDIR)/%.c
#    $(CC) $(CFLAGS) -c -o $@ $<
#
#$(OBJDIR)/%.o: $(SRCDIR)/%.cpp
#    $(CXX) $(CXXFLAGS) -c -o $@ $<

