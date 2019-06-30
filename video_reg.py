import boto3
import json
import sys
import csv
import math
import statistics
import time
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

f = open("shining_response.txt", "r")
# f = open("dull_face.txt", "w+")

# with open('credentials.csv', 'r') as input:
#     next(input)
#     reader = csv.reader(input)
#     for line in reader:
#         access_key_id = line[2]
#         secret_access_key = line[3]

#Analyzes videos using the Rekognition Video API 
class VideoDetect:
    jobId = ''
    rek = boto3.client('rekognition')
    queueUrl = 'https://sqs.us-east-1.amazonaws.com/379232480951/RekognitionQueue'
    roleArn = 'arn:aws:iam::379232480951:role/service_Rekognition'
    topicArn = 'arn:aws:sns:us-east-1:379232480951:AmazonRekognitionTopic'
    bucket = 'video-reg'
    video = 'trim.mp4'


    def main(self):

        jobFound = False
        sqs = boto3.client('sqs')

        response = self.rek.start_face_detection(Video={'S3Object':{'Bucket':self.bucket,'Name':self.video}},
           NotificationChannel={'RoleArn':self.roleArn, 'SNSTopicArn':self.topicArn},
           FaceAttributes="ALL") 

        print('Starting Our Super Secret Scoring')
        dotLine=0
        while jobFound == False:
            sqsResponse = sqs.receive_message(QueueUrl=self.queueUrl, MessageAttributeNames=['ALL'],
                                          MaxNumberOfMessages=10)
            if sqsResponse:
                
                if 'Messages' not in sqsResponse:
                    if dotLine<20:
                        print('.', end='')
                        dotLine=dotLine+1
                    else:
                        print()
                        dotLine=0    
                    sys.stdout.flush()
                    continue

                for message in sqsResponse['Messages']:
                    notification = json.loads(message['Body'])
                    rekMessage = json.loads(notification['Message'])
                    if str(rekMessage['JobId']) == response['JobId']:
                        print('Finished Processing!')
                        print()
                        jobFound = True
                        self.GetResultsFaces(rekMessage['JobId'])             

                        sqs.delete_message(QueueUrl=self.queueUrl,
                                       ReceiptHandle=message['ReceiptHandle'])
                    else:
                        print("Job didn't match:" +
                              str(rekMessage['JobId']) + ' : ' + str(response['JobId']))
                    sqs.delete_message(QueueUrl=self.queueUrl,
                                   ReceiptHandle=message['ReceiptHandle'])


    def GetResultsFaces(self, jobId):
        maxResults = 10
        paginationToken = ''
        finished = False
        std = []
        while finished == False:
            response = self.rek.get_face_detection(JobId=jobId,
                                            MaxResults=maxResults,
                                            NextToken=paginationToken)

            # print(response['VideoMetadata']['Codec'])
            # print(str(response['VideoMetadata']['DurationMillis']))
            # print(response['VideoMetadata']['Format'])
            # print(response['VideoMetadata']['FrameRate'])
            for faceDetection in response['Faces']:
                emotions = faceDetection['Face']['Emotions']
                emotions.sort(key=lambda x:x['Type'])
                list_val = 0
                for l in emotions:
                    # print("Emotion", l.get('Type'))
                    line = f.readline()
                    val = float(line)
                    # print('val:', val)
                    list_val += (abs((val - l['Confidence'])))
                    # print("Confidence", l.get('Confidence'))
                #     f.write(str(l['Confidence']))
                #     f.write("\n")
                # f.write("\n")
                f.readline()
                std.append(list_val / 2)
            if 'NextToken' in response:
                paginationToken = response['NextToken']
            else:
                finished = True
        print ('Final score:', 100 - statistics.mean(std))

def upload_and_trim(vid_name):
    s3 = boto3.client('s3')
    ffmpeg_extract_subclip(vid_name, 0, 10, targetname="trim.mp4")
    filename = "trim.mp4"
    bucket_name = 'video-reg'
    s3.upload_file(filename, bucket_name, filename)
    

if __name__ == "__main__":

    vid_name = input("Type video name: ")
    upload_and_trim(vid_name)
    print("Uploading to S3...")
    time.sleep(5)
    analyzer=VideoDetect()
    analyzer.main()
    s3 = boto3.resource('s3')
    print("Cleaning up")
    s3.Object('video-reg', 'trim.mp4').delete()


