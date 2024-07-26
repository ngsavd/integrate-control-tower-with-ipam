# Using Amazon IPAM to enhance AWS Control Tower governance for Networking resources

This project implements a solution which integrates Amazon IPAM within AWS Control Tower through the use of Lifecycle Events. It presents the architecture view and shows how this solution extends your AWS Control Tower environment with Amazon IPAM to allow teams to access IPAM pools for their workload accounts.It is based on this [**blog](https://aws.amazon.com/blogs/mt/using-amazon-ipam-to-enhance-aws-control-tower-governance-for-networking-resources/)

# Solution Overview:

When the solution is deployed using CloudFormation, the following components are created as part of the architecture:
    1. IPAM instance in the Networking account with a top-level pool and child pools created within IPAM scope.
    2. Custom CloudFormation resource backed by a Lambda function in the Networking account which creates the IPAM pool hierarchy.
    3. The Lambda function in the management account that listens for events from AWS Control Tower Lifecycle event “CreateManagedAccount”

The Figure below shows the sequence of events when the CloudFormation is deployed, cloud administrator creates a new account in AWS Control Tower and an application developer creates a VPC.

![Sequence_Flow_Diagram_CT_IPAM](https://github.com/aws-samples/integrate-control-tower-with-ipam/assets/173191727/33d14e08-0504-4dd5-8255-fd58c88a3bc1)

## IPAM pool creation in the Networking Account
    1.When the CloudFormation template is deployed in the AWS Control Tower management account it uses Stacksets to deploy resources in the Networking account.
    2.This in turn creates a stack and a CloudFormation Custom Resource in the Networking account.
    3.The Custom Resource is backed by a Lambda function which creates the IPAM pool structures comprising of the top-level pool, Regional pools for the Regions specified and environment pools for each Region.

## When a new account is created in AWS Control Tower through Account Factory:
    4.The CreateManagedAccount lifecycle event triggers the CTIPAMLifeCycleLambda Lambda function.
    5.The Lambda function assumes the AWSControlTowerExecution role in the networking account and invokes AWS Resource Access Manager (RAM)
    6.RAM shares only the IPAM pools that matches the allocation tag of the pool with the member account’s OU name.
    7.In the member account, you can now create VPCs with the shared IPAM pools applicable for that Region.

# Deploy the solution
## Prerequisites
1. This solution requires a AWS Control Tower landing zone setup in your account. 
Refer to this [**guide](https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html) to setup your AWS Control Tower.

2. In your AWS Control Tower environment, identify the networking account. If it does not exist, create a Networking account which will hold your networking resources. For this solution, Networking account will be setup as a delegated administrator for IPAM. The parent OU of Networking account can be as per your existing structure or as per your choice. Make a note of the Networking account id.

3. Create an OU structure for your Workload Accounts to represent your environments. Example shown here talk about 2 environments Production and SDLC and Figure 1 shows 2 OUs Prod OU and SDLC OU. Make note of these OU names in your environment.

4. If using the AWS CLI, Ensure that the AWS CLI is installed and configured with the appropriate credentials and region. For console access  Navigate to the AWS Management Console and log in with your credentials.

## Deployment Steps
### For first time deployment: 
Deploying a solution in AWS for the first time using source code from GitHub involves several steps. Here’s a step-by-step guide to help you deploy using AWS CloudFormation.
You can reference the Deployment Steps section of the blog post for details.
### Step 1: Deploy your CloudFormation templates to S3 bucket
   - Go to the **S3** service in the AWS Management Console.
   - Click on your bucket or create a new one.
   - Click on the **Upload** button and select your Cloudformation template files from the templates folder.
   - Note the **S3 Bucket and Path URL**  for later use in Step 3.

### Step 2: Upload Your Lambda Packages to S3

1. **Upload the Packages**: If you haven't done this already, upload your Lambda package zip files to an S3 bucket.
   - Go to the **S3** service in the AWS Management Console.
   - Click on your bucket or create a new one.
   - Click on the **Upload** button and select your zip files from the packages folder (`ctipam_ct_integration_1.0.0.zip` and `ctipam_helper_1.0.0.zip`).
   - Note the **Bucket Name** and **Key Prefix** (if any) for later use in Step 3.

### Step 3: Deploy using CloudFormation

1. **Launch CloudFormation Stack**: Launch CloudFormation stack using the cloudformation template **ipam-controltower-integration.template.yaml** from the templates folder of this repo.

2. **Modify Parameters**: You should adjust the parameters in the CloudFormation template- `LambdaBucket` and `LambdaPrefix` parameters for your template, based on values from Step 2. You should adjust the paramter `RepoRootURL` for your template based on value from Step 1. Specify other parameters as required for your setup.


### Step 4: Monitor and Validate Deployment

1. **Monitor the Stack Creation**:
   - You can monitor the progress of your stack creation in the **Events** tab of the CloudFormation console.
   - Ensure that all resources are created successfully and there are no errors.

2. **Verify the Deployment**:
   - After stack creation is complete, verify that your Lambda functions are correctly deployed.
   - Check the **Lambda** service to ensure your functions are listed and properly configured.

### To update the code of existing deployment
To update your Lambda function and create a new package file, you can follow these steps. This guide assumes you're working on a local development environment and have the necessary permissions to modify and deploy Lambda functions.

#### 1. Modify the Lambda Function Code

   1. Ensure you have the `index.py` file you want to modify(cti-intergation-lambda or ipam-pool-lambda). 

   2. Make your necessary code changes to `index.py` within the Lambda function’s directory.

#### 2. Prepare the New Package
1. Run the following commands for creating the package for the lambda function **ct-integration-lambda**
```
cd ct-integration-lambda/
zip ../packages/ctipam_ct_integration_1.0.0.zip index.py ../libraries/*
```

2. Run the following commands for creating the package for the lambda function **ipam-pool-lambda**
```
cd ipam-pool-lambda/
zip ../packages/ctipam_helper_1.0.0.zip index.py ../libraries/*
```

#### 3. Update Lambda Function in AWS

1. **Upload the New Package to S3**:
   - If you’re using AWS S3 for Lambda packages, upload the new zip file to your S3 bucket.
   ```bash
   aws s3 cp ctipam_ct_integration_1.0.0.zip s3://your-bucket-name/path/to/ctipam_ct_integration_1.0.0.zip
   aws s3 cp ctipam_helper_1.0.0.zip s3://your-bucket-name/path/to/ctipam_helper_1.0.0.zip
   ```

2. **Update Lambda Function via AWS Management Console**:
   - Go to the **Lambda** service in the AWS Management Console.
   - Select the function you are updating.
   - Choose **Upload from Amazon S3** or **Upload from file** and select your new zip file.

3. **Update Lambda Function via AWS CLI**:
   - Alternatively, you can use the AWS CLI to update your Lambda function.
   ```bash
   aws lambda update-function-code --function-name your-lambda-function-name --s3-bucket your-bucket-name --s3-key path/to/ctipam_ct_integration_1.0.0.zip
   aws lambda update-function-code --function-name your-lambda-function-name --s3-bucket your-bucket-name --s3-key path/to/ctipam_helper_1.0.0.zip
   ```

#### 4. Test the Updated Lambda Function

1. **Verify the Update**:
   - After updating the Lambda function, test it using the AWS Management Console or AWS CLI.
   - Check CloudWatch logs to ensure there are no errors and that the function operates as expected.

2. **Debug if Necessary**:
   - Review CloudWatch logs and any error messages to troubleshoot issues that may arise from the update.




## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

