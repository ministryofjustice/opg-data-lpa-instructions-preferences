package main

import (
	"cmp"
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
)

func setup(ctx context.Context, bucketName string) (*s3.Client, error) {
	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		return nil, err
	}

	cfg.BaseEndpoint = new(cmp.Or(os.Getenv("AWS_BASE_URL"), "http://localhost:4566"))
	cfg.Region = "eu-west-1"

	s3Client := s3.NewFromConfig(cfg, func(opts *s3.Options) {
		opts.UsePathStyle = true
	})

	objects, err := s3Client.ListObjects(ctx, &s3.ListObjectsInput{
		Bucket: new(bucketName),
	})
	if err == nil {
		var identifiers []types.ObjectIdentifier
		for _, object := range objects.Contents {
			identifiers = append(identifiers, types.ObjectIdentifier{
				Key: object.Key,
			})
		}

		s3Client.DeleteObjects(ctx, &s3.DeleteObjectsInput{
			Bucket: new(bucketName),
			Delete: &types.Delete{
				Objects: identifiers,
			},
		})
	}

	if _, err := s3Client.CreateBucket(ctx, &s3.CreateBucketInput{
		Bucket: new(bucketName),
		CreateBucketConfiguration: &types.CreateBucketConfiguration{
			LocationConstraint: types.BucketLocationConstraint(types.BucketLocationConstraintEuWest1),
		},
	}); err != nil {
		var already *types.BucketAlreadyOwnedByYou
		if !errors.As(err, &already) {
			return nil, err
		}
	} else {
		if err := s3.NewBucketExistsWaiter(s3Client).Wait(
			ctx,
			&s3.HeadBucketInput{Bucket: new(bucketName)},
			time.Minute,
		); err != nil {
			return nil, fmt.Errorf("waiting for bucket: %w", err)
		}
	}

	return s3Client, nil
}

func TestDryRun(t *testing.T) {
	var (
		ctx        = context.Background()
		bucketName = "my-test-bucket"
	)

	s3Client, err := setup(ctx, bucketName)
	if err != nil {
		t.Fatalf("setup: %v", err)
	}

	slog.SetDefault(slog.New(slog.DiscardHandler))

	for key, body := range map[string]string{
		"good-instructions.jpg": "hey",
		"good-preferences.jpg":  "hey",
		"bad-instructions.jpg":  "",
		"bad-preferences.jpg":   "",
	} {
		if _, err := s3Client.PutObject(ctx, &s3.PutObjectInput{
			Bucket: new(bucketName),
			Key:    new(key),
			Body:   strings.NewReader(body),
		}); err != nil {
			t.Fatalf("put object: %v", err)
		}
	}

	if err := processBucket(ctx, s3Client, bucketName, false); err != nil {
		t.Errorf("error returned: %v", err)
	}

	listOutput, err := s3Client.ListObjects(ctx, &s3.ListObjectsInput{
		Bucket: new(bucketName),
	})
	if err != nil {
		t.Errorf("error returned: %v", err)
	}

	var keys []string
	for _, item := range listOutput.Contents {
		keys = append(keys, *item.Key)
	}

	slices.Sort(keys)
	if expected := []string{
		"bad-instructions.jpg",
		"bad-preferences.jpg",
		"good-instructions.jpg",
		"good-preferences.jpg",
	}; !slices.Equal(keys, expected) {
		t.Errorf("bucket items do not match expected.\nGot: %v\nExpected: %v", keys, expected)
	}
}

func TestRun(t *testing.T) {
	var (
		ctx        = context.Background()
		bucketName = "my-other-test-bucket"
	)

	s3Client, err := setup(ctx, bucketName)
	if err != nil {
		t.Fatalf("setup: %v", err)
	}

	slog.SetDefault(slog.New(slog.DiscardHandler))

	for _, key := range []string{"good-instructions.jpg", "good-preferences.jpg"} {
		if _, err := s3Client.PutObject(ctx, &s3.PutObjectInput{
			Bucket: new(bucketName),
			Key:    new(key),
			Body:   strings.NewReader("hey"),
		}); err != nil {
			t.Fatalf("put object: %v", err)
		}
	}

	for i := range 2000 {
		if _, err := s3Client.PutObject(ctx, &s3.PutObjectInput{
			Bucket: new(bucketName),
			Key:    new(fmt.Sprintf("bad-%d.jpg", i)),
			Body:   strings.NewReader(""),
		}); err != nil {
			t.Fatalf("put object: %v", err)
		}
	}

	if err := processBucket(ctx, s3Client, bucketName, true); err != nil {
		t.Errorf("error returned: %v", err)
	}

	listOutput, err := s3Client.ListObjects(ctx, &s3.ListObjectsInput{
		Bucket: new(bucketName),
	})
	if err != nil {
		t.Errorf("error returned: %v", err)
	}

	var keys []string
	for _, item := range listOutput.Contents {
		keys = append(keys, *item.Key)
	}

	slices.Sort(keys)
	if expected := []string{
		"good-instructions.jpg",
		"good-preferences.jpg",
	}; !slices.Equal(keys, expected) {
		t.Errorf("bucket items do not match expected.\nGot: %v\nExpected: %v", keys, expected)
	}
}
