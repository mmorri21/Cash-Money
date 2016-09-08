############################################################################################

# ALTERNATIVE METHOD TO GET DATA: PACKAGE quantmod (http://www.quantmod.com/examples/intro/)

library(quantmod)

ticker_list <- c("NAV", "PCAR")
getSymbols(ticker_list, src="google")
barChart(NAV)