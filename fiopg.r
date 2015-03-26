setwd(dir)
poly=1
hist=1
ppi <- 300

# graph writes  by 3 user loads
# for each user load graph the different blocksizes

for(i in 1:(length(l)/2) ) {
    testname <- l[i,][1]
    bs <- l[i,][2]
    file <- paste(testtype,testname,"bs",bs,sep="_")
    file <- paste(file,".png",sep="")
    cat("file=",file,"\n")
    png(filename=file, width=6*ppi, height=6*ppi, res=ppi )
    if ( bs == "1024K") {
        title=paste(testtype,testname,"bs=1M")
    } else {
        title=paste(testtype,testname,paste("bs=",bs,sep=""))
    }
    graphit(m, i_name=testname, i_bs=bs,i_title=title,i_hist=hist,i_poly=poly)
    dev.off()
}



