import findspark
findspark.init()

import pandas as pd
import re
import csv
from nltk.corpus import stopwords
from nltk import pos_tag, word_tokenize
from nltk.stem.porter import *

from pyspark import SparkContext, SparkConf
from pyspark import RDD
from pyspark.sql import SparkSession, SQLContext
from pyspark.sql.types import *
from pyspark.sql.functions import udf, lower, col, split
from pyspark.ml.feature import Tokenizer, RegexTokenizer, StopWordsRemover, NGram
from pyspark.ml.feature import HashingTF, IDF, CountVectorizer

conf = SparkConf().setAppName("PySpark Recipe Generation Project")
sc = SparkContext(conf=conf)

spark = SparkSession \
    .builder \
    .appName("PySpark Recipe Generation Project") \
    .config("spark.some.config.option", "some-value") \
    .getOrCreate()

schema = StructType([
    StructField("id", IntegerType()),
    StructField("made_it_count", IntegerType()),
    StructField("rating", DoubleType()),
    StructField("time", IntegerType()),
    StructField("title", StringType()),
    StructField("direction", StringType()),
    StructField("ingredient", StringType())
])

df = spark.read.csv("/Users/Jiajia/Google Drive/Columbia/Big Data/Recipes.csv", header=True, schema=schema)
#print df.count()
#df.printSchema()
#df.show()

df.ingredient = df.select(split(df.ingredient, ',').alias('ingredient'))     #still a string
df.ingredient = df.select(lower(df.ingredient).alias('ingredient'))
df.direction = df.select(lower(df.direction).alias('direction'))

'''
#### Cooking Methods
methodDF = df.select("id", "direction")
mwordsDF = Tokenizer(inputCol="direction", outputCol="words").transform(methodDF)
#regexTokenizer = RegexTokenizer(inputCol="direction", outputCol="words", pattern="\\W")    #Java patterns
mwordsDF = StopWordsRemover(inputCol="words", outputCol="simple_words").transform(mwordsDF)
mwordsDF = NGram(inputCol="simple_words", outputCol="ngrams").transform(mwordsDF)
'''

## Identify Ingredients
# units: http://www.recipetips.com/kitchen-tips/t--482/units-of-measure.asp
stemmer = PorterStemmer()
units = ['tsp','teaspoon','cup','gill','drop','tbsp','tablespoon','pt','pint','dash','oz','ounce','fl oz','fluid' \
	'qt','quart','gram','gal','gallon','lb','pound','pottle','peck','bushel','pinch','degrees F','degrees C','inch', \
	'package', 'piece', 'can', 'bunch', 'jar']
units = [stemmer.stem(i) for i in units]

recingr = []
for ingrow in df.select('ingredient','id').collect():    #Row object 
	try:
		ingred = ingrow.ingredient
		print ingred
		text = word_tokenize(ingred)
		tagged = pos_tag(text)
		newingred = ' '.join([i[0] for i in tagged if i[1] in ['NN','NNS','NNPS','NNP','JJ',',']])
		newingred = re.sub(r'(\d+)|(\d*/?\d*)', '', newingred)
		newingred = ' '.join([i for i in newingred.split(' ') if stemmer.stem(i) not in units])	
		inglist = newingred.split(',')
		inglist = [i.strip(' ') for i in inglist]
		recingr.append(inglist)
	except:
		continue

recingr_new = []
pureingr = []
for ingl in recingr:
	for ing in ingl:
		if ing != '':
			pureingr.append(ing)
		else:
			ingl.remove(ing)
	newingl = ','.join(ingl).encode('utf8')
	recingr_new.append(newingl)

## Wordcount for Ingredients
ingRDD = sc.parallelize(pureingr)
ingCount = ingRDD.map(lambda x: (x,1)).reduceByKey(lambda x,y: x+y).map(lambda (k,v): (v,k)).sortByKey(False)

## Nodes: top 1960 ingredients
popCount = ingCount.collect()[0:3000]
popingr = [i[1].encode('utf8') for i in popCount if i[0] > 2]   
print popingr

with open('nodes.csv', 'wb') as myfile:
	wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
	for node in popingr:
		wr.writerow([node])

with open('recipe_ingred.csv', 'wb') as myfile2:
	wr2 = csv.writer(myfile2, quoting=csv.QUOTE_ALL)
	for row in recingr_new:
		wr2.writerow([row])


'''
# ISSUE??
cv = CountVectorizer(inputCol="ngrams", outputCol="features", vocabSize=30)
model = cv.fit(wordsDF)
result = model.transform(wordsDF).show(truncate=False)

sentenceData = spark.createDataFrame([
    (0, "Hi I"),
    (0, "I wish"),
    (1, "Logistic regression models is I neat")
], ["label", "sentence"])
tokenizer = Tokenizer(inputCol="sentence", outputCol="words")
wordsData = tokenizer.transform(sentenceData)
hashingTF = HashingTF(inputCol="words", outputCol="rawFeatures", numFeatures=20)
featurizedData = hashingTF.transform(wordsData)
for features_label in featurizedData.select("rawFeatures", "label").take(3):
    print(features_label)
# alternatively, CountVectorizer can also be used to get term frequency vectors

idf = IDF(inputCol="rawFeatures", outputCol="features")
idfModel = idf.fit(featurizedData)
rescaledData = idfModel.transform(featurizedData)
for features_label in rescaledData.select("features", "label").take(3):
    print(features_label)
'''