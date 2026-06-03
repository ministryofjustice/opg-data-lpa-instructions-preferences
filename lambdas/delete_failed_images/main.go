// Provides an AWS lambda function "delete-failed-images"
//
// Requires the environment variable BUCKET_NAME to be set to the bucket to
// iterate over. By default it will log the images that it would delete, call
// with body `{"Delete": true}` to actually delete them.
//
// Will continue if an error occurs when trying to delete objects, logging the
// errors for later inspection.
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
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
)

var (
	s3Client   *s3.Client
	bucketName string
)

func main() {
	ctx := context.Background()
	awsBaseURL := os.Getenv("AWS_BASE_URL")
	bucketName = os.Getenv("BUCKET_NAME")

	if bucketName == "" {
		slog.Error("BUCKET_NAME unset")
		return
	}

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

		var toDelete []types.ObjectIdentifier

		for _, object := range output.Contents {
			if *object.Size == 0 {
				toDelete = append(toDelete, types.ObjectIdentifier{Key: object.Key})
			}
		}

		if doDelete {
			out, err := s3Client.DeleteObjects(ctx, &s3.DeleteObjectsInput{
				Bucket: new(bucketName),
				Delete: &types.Delete{
					Objects: toDelete,
				},
			})
			if err != nil {
				for _, object := range toDelete {
					slog.Error("error deleting object", slog.String("key", *object.Key), slog.String("err", err.Error()))
				}
				continue
			}

			for _, error := range out.Errors {
				slog.Info("error deleting object", slog.String("key", *error.Key), slog.String("msg", *error.Message))
			}

			for _, object := range out.Deleted {
				slog.Info("deleted", slog.String("key", *object.Key))
			}
		} else {
			for _, object := range toDelete {
				slog.Info("should delete", slog.String("key", *object.Key))
			}
		}
	}

	return nil
}
