package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

var (
	s3Client   *s3.Client
	bucketName string
)

func main() {
	ctx := context.Background()
	awsBaseURL := os.Getenv("AWS_BASE_URL")
	bucketName = os.Getenv("BUCKET_NAME")

	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		slog.Error(fmt.Sprintf("load config: %v", err))
		return
	}

	if awsBaseURL != "" {
		cfg.BaseEndpoint = aws.String(awsBaseURL)
	}

	s3Client = s3.NewFromConfig(cfg)

	lambda.Start(run)
}

type Event struct {
	Delete bool
}

func run(ctx context.Context, event Event) error {
	slog.Info("started run", slog.String("bucketName", bucketName), slog.Bool("delete", event.Delete))

	if err := processBucket(ctx, s3Client, bucketName, event.Delete); err != nil {
		slog.Error(fmt.Sprintf("error processing bucket: %v", err))
		return err
	}

	return nil
}

func processBucket(ctx context.Context, s3Client *s3.Client, bucketName string, doDelete bool) error {
	paginator := s3.NewListObjectsV2Paginator(s3Client, &s3.ListObjectsV2Input{
		Bucket: new(bucketName),
	})

	for paginator.HasMorePages() {
		output, err := paginator.NextPage(ctx)
		if err != nil {
			return err
		}

		for _, object := range output.Contents {
			meta, err := s3Client.HeadObject(ctx, &s3.HeadObjectInput{
				Bucket: new(bucketName),
				Key:    object.Key,
			})
			if err != nil {
				return err
			}

			if meta.Metadata["processerror"] == "1" {
				if doDelete {
					_, err := s3Client.DeleteObject(ctx, &s3.DeleteObjectInput{
						Bucket: new(bucketName),
						Key:    object.Key,
					})
					if err != nil {
						return err
					}
					slog.Info("deleted", slog.String("key", *object.Key))
				} else {
					slog.Info("should delete", slog.String("key", *object.Key))
				}
			}
		}
	}

	return nil
}
