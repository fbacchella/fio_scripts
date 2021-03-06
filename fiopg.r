setwd(dir)
poly=1
hist=1
ppi <- 300

for (i in 1:dim(jobs)[1]) {
    testname <- jobs[i,1]
    bs <- jobs[i,2]
    users <- jobs[i,3]
    if(bs != "undefined") {
        label <- "bs"
        value <- bs
    } else if(users > 0) {
        label <- "users"
        value <- users
    }
    file <- paste(testtype,testname, label, value, sep="_")
    file <- paste(file,".png",sep="")
    cat("file=",file,"\n")
    png(filename=file, width=6*ppi, height=6*ppi, res=ppi )
    if ( label== "bs" && bs == "1024K") {
        title=paste(testtype,testname,"bs=1M")
    } else {
        title=paste(testtype,testname,paste(label, "=",value, sep=""))
    }
    graphit(m, i_name=testname, i_bs=bs, i_user=users, i_title=title, i_hist=hist, i_poly=poly)
    dev.off()
}


