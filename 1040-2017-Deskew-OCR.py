import re
import os
import math
import pyocr
import pyocr.builders
import numpy as np
import cv2
from PIL import Image
from alyn import Deskew

INPUT_IMAGE = "images/2017_1040.png"						# 6/6
#INPUT_IMAGE = "images/2017_1040-sm.png" 					# 6/6
#INPUT_IMAGE = "images/2017_1040-lg.png"					# 6/6
#INPUT_IMAGE = "images/2017_1040-xl.png"					# 6/6	
#INPUT_IMAGE = "images/2017_1040_borders.png"				# 6/6
#INPUT_IMAGE = "images/2017_1040_borders-dramatic.png"		# 6/6
#INPUT_IMAGE = "images/2017_1040_skewed.png"				# 6/6
#INPUT_IMAGE = "images/2017_1040_skewed-cc.png"				# 5/6 (Missed income: "" -- OCR error)
#INPUT_IMAGE = "images/2017_1040_skewed-dramatic.png"		# MemoryError?
#INPUT_IMAGE = "images/2017_1040_skewed-lg.png"				# 5/6 (Missed city: "" -- OCR error)

DESKEWED_IMAGE = "Deskewed.png"
CONTOURED_IMAGE = "Contoured.png"
CROPPED_IMAGE = "Cropped.png"

STRING = "STRING"
NUMBER = "NUMBER"

fields = {
	"firstName" : ((0,128),(482,166), STRING),
	"lastName" : ((508,128),(1194,166), STRING),
	"ssn" : ((1209,128),(1506,166), NUMBER),
	"address" : ((0,263),(1053,299), STRING),
	"city" :  ((0,331),(1176,366), STRING),
	"totalIncome" : ((1247,1974),(1506,2000), NUMBER)
}

X_TRANSLATION = 0
Y_TRANSLATION = 0
TEMPLATE_WIDTH = 1506
TEMPLATE_HEIGHT = 2035

tools = pyocr.get_available_tools()[0]

def deskew(input_file):
	d = Deskew(
		input_file=input_file,
		display_image='No',
		output_file=DESKEWED_IMAGE,
		r_angle=0)
	d.run()
	
def crop(input_file, output_file, start, end):
	print "Cropping between %s and %s" % (str(start), str(end))
	img = Image.open(input_file)
	crop_img = img.crop((start[0], start[1], end[0], end[1]))
	crop_img = crop_img.convert('L')
	crop_img.save(output_file)

def analyze(contour):
	global largest_x, largest_y, smallest_x, smallest_y

	if type(contour) is np.ndarray:
		if len(contour) == 2:
			x = contour[0]
			y = contour[1]
			if x > largest_x:
				largest_x = x
			if x < smallest_x:
				smallest_x = x
			if y > largest_y:
				largest_y = y
			if y < smallest_y:
				smallest_y = y
		else:
			for element in contour:
				analyze(element)
	else:
		print "Type is not ndarray %d" % contour
		
def readText(file_name):
	text = tools.image_to_string(
		Image.open('crop/' + file_name + '.jpg'), 
		lang="eng",
		builder=pyocr.builders.DigitBuilder()
	)
	return text

'''
Clean up temp files first
'''
try:
	os.remove(DESKEWED_IMAGE)
	os.remove(CONTOURED_IMAGE)
	os.remove(CROPPED_IMAGE)
except WindowsError:
	pass
	
'''
Deskew image before performing OCR
'''
deskew(INPUT_IMAGE)

'''
Load deskewed image and crop to text area
'''
# Load the image
img = cv2.imread(DESKEWED_IMAGE, 1)

imgray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
ret,thresh = cv2.threshold(imgray,127,255,0)
im2, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

# Save image with contours drawn for debug pruposes
cv2.drawContours(img, contours, -1, (0,255,0), 3)
cv2.imwrite(CONTOURED_IMAGE, img)

# Delete the first contour which will be the full width/height of image
del contours[0]

largest_x = 0
largest_y = 0
smallest_x = float("inf")
smallest_y = float("inf")
	
for contour in contours:
	analyze(contour)

# Crop image to area of contours i.e. the text on the page
crop(DESKEWED_IMAGE, CROPPED_IMAGE, (smallest_x, smallest_y), (largest_x, largest_y))

'''
START OF OCR PROCESSING
'''

'''
Open document and get dimensions
'''
img = Image.open(CROPPED_IMAGE)
DOCUMENT_WIDTH, DOCUMENT_HEIGHT = img.size

'''
Perform Scaling Adjustment
'''
X_SCALE_RATIO = (DOCUMENT_WIDTH * 1.0) / TEMPLATE_WIDTH
Y_SCALE_RATIO = (DOCUMENT_HEIGHT * 1.0) / TEMPLATE_HEIGHT

print X_SCALE_RATIO
print Y_SCALE_RATIO

for field in fields.keys():
	# eg. "firstName" : ((49,107),(285,126), STRING),
	# Adjust start x and y
	# Adjust end x and y
	
	print field
	print fields[field]
	
	start_x = fields[field][0][0]
	start_y = fields[field][0][1]
	end_x = fields[field][1][0]
	end_y = fields[field][1][1]
	
	fields[field] = (
		(start_x * X_SCALE_RATIO, start_y * Y_SCALE_RATIO),
		(end_x * X_SCALE_RATIO, end_y * Y_SCALE_RATIO),
		fields[field][2]
	)
	
	print fields[field]

'''
Crop each field into separate image for OCR processing
'''
for field in fields.keys():
	fieldStart = fields[field][0]
	fieldEnd = fields[field][1]
	crop(CROPPED_IMAGE, "crop/%s.jpg" % field, fieldStart, fieldEnd)

print "\nFields:"
print "====================="

'''
Perform ocr on each cropped image
'''
for field in fields.keys():
	value = readText(field)
	
	if fields[field][2] == NUMBER:
		value = re.sub("[^0-9]", "", value)
	
	print "%s => %s" % (field, value.encode("utf-8"))	


