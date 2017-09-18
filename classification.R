library(dplyr)
library(readr)
library(tidyr)
library(pamr)

# load data
setwd('/Users/dt/Documents/UChicago/Literature/2. Gender and verbs')
percentage_data <- read_csv("percent.csv")

############### 10-FOLD X-VAL & CLASSIFICATION OF HELD OUT DATA ###############
set.seed(1966) # for repeatability
features <- colnames(percentage_data)[9:ncol(percentage_data)]
signalColumn <- "pn_gender"
signals <- percentage_data[,signalColumn]
signalColors <- 1*(signals=="M")
the_data <- as.matrix(percentage_data[,-c(1:8)])
male_rows <- which(percentage_data$pn_gender == "M")
female_rows <- which(percentage_data$pn_gender == "F")
all_rows <- c(male_rows, female_rows)
train <-  c(sample(male_rows, 3000), sample(female_rows, 3000))
# Hold out 658 rows for testing later
test <- all_rows[-train]

# Perform feature selection and 10-fold x-validation... 
data.train <- list(x=t(the_data[train,]), y=signalColors[train], geneid=features)
prior <- rep(1/length(levels(as.factor(data.train$y))), length(levels(as.factor(data.train$y))))
pamr.train.out <- pamr.train(data.train, prior=prior)
new.scales <- pamr.adaptthresh(pamr.train.out)
pamr.train.out <- pamr.train(data.train, prior=prior, threshold.scale=new.scales)
pamr.cv.out <- pamr.cv(pamr.train.out, data.train)

### How did the machine perform in 10-fold xval. . . 
thresh.row <- which(pamr.cv.out$error == min(pamr.cv.out$error))[1]
the.thresh <- pamr.cv.out$threshold[thresh.row]
tt <- pamr.confusion(pamr.cv.out,  threshold=the.thresh, FALSE)
pamr.confusion(pamr.cv.out,  threshold=new.scales)

# x-validation results are as follows with random seed 1966
# 0    1 Class Error rate
# 0 2327  673        0.2243333
# 1  488 2512        0.1626667
# Overall error rate= 0.193

# What were the most useful features
feature.data <- pamr.listgenes(pamr.train.out, data.train, threshold=new.scales, pamr.cv.out, genenames=TRUE)
write.csv(feature.data, 'feature_data.csv')

# Now test model performance on the held out data.
data.test <- list(x=t(the_data[test,]), geneid=features)
pamr.test.pred <- pamr.predict(pamr.train.out, data.test$x, threshold=1)
out <- data.frame(pn_gender = percentage_data[test, "pn_gender"], pred=as.character(pamr.test.pred), stringsAsFactors = F)
male_pn <- which(out$pred == "1")
out$pred <- "F"
out[male_pn, "pred"] <- "M"
correct <- which(out$pn_gender == out$pred)
length(correct)/nrow(out)
# with set.seed(1966)
# we observe accuracy of 0.7948328

# What do the misclassifications look like. . . 
misclassed_M <- filter(out, pn_gender == "M" & pred == "F")
nrow(misclassed_M)/329

misclassed_F <- filter(out, pn_gender == "F" & pred == "M")
nrow(misclassed_F)/329

# What were the top 50 features for each pronoun class:
feature.data_df <- data.frame(feature.data, stringsAsFactors = F)
colnames(feature.data_df)<-c("id", "F_score", "M_score", "av.rank.in.CV", "prop.selected.in.CV")

f_features <- feature.data_df[which(feature.data_df$F_score > 0), "id"]
paste(f_features[1:50], collapse = ", ") # female pronoun verbs

m_features <- feature.data_df[which(feature.data_df$M_score > 0), "id"]
paste(m_features[1:50], collapse = ", ") # male pronoun verbs
