# Using Amazon IPAM to enhance AWS Control Tower governance for Networking resources

This project implements a solution which integrates Amazon IPAM within AWS Control Tower through the use of Lifecycle Events. It presents the architecture view and shows how this solution extends your AWS Control Tower environment with Amazon IPAM to allow teams to access IPAM pools for their workload accounts.It is based on this (detailed) blog:https://aws.amazon.com/blogs/mt/using-amazon-ipam-to-enhance-aws-control-tower-governance-for-networking-resources/

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
1.This solution requires a AWS Control Tower landing zone setup in your account. 
Refer to this guide to setup your AWS Control Tower.

2.In your AWS Control Tower environment, identify the networking account. If it does not exist, create a Networking account which will hold your networking resources. For this solution, Networking account will be setup as a delegated administrator for IPAM. The parent OU of Networking account can be as per your existing structure or as per your choice but consider following multi-account best practices and create it under Infrastructure OU. Make a note of the Networking account id.

3.Create an OU structure for your Workload Accounts to represent your environments. Example shown here talk about 2 environments Production and SDLC and Figure 1 shows 2 OUs Prod OU and SDLC OU. Make note of these OU names in your environment.

Deployment Steps

In the AWS Control Tower management account, go to the Amazon VPC IP Address Manager console, select settings and click on edit to specify the Networking account id under the delegated administrator account.

The networking account would be delegated as the IPAM administrator.
Figure 5. Delegating the Networking Account as IPAM Administrator

Figure 5. Delegating the Networking Account as IPAM Administrator
Figure 6. Verify that the Networking Account is delegated as the IPAM Administrator

Figure 6. Verify that the Networking Account is delegated as the IPAM Administrator

    Login to the AWS Control Tower management account, go to the AWS Resource Access Manager console. On the Settings page, select the Enable sharing with AWS Organizations check box.

Figure 7. On the Settings page, the Enable sharing with AWS Organizations check box is selected.

Figure 7. On the Settings page, the Enable sharing with AWS Organizations check box is selected.

Login to the networking account, go to Amazon VPC IP Address Manager console . Select Create IPAM and then Select the check box to Allow Amazon VPC IP Address Manager to replicate data from the member account(s) into the Amazon VPC IP Address Manager delegate account.

Figure 8. Creating IPAM Pool

Figure 8. Creating IPAM Pool

    Provide Name, Description and Operating Regions for the Amazon VPC IP Address Manager.

Figure 9. Populating the IPAM Pool details

Figure 9. Populating the IPAM Pool details

    When you create IPAM instance, Amazon automatically does the following:

        Returns a globally unique resource ID (IpamId) for the IPAM.
        Creates a default public scope (PublicDefaultScopeId) and a default private scope (PrivateDefaultScopeId).

    In the Amazon VPC IP Address Manager console, go to Scopes and make note of the  PrivateDefaultScopeId

Figure 10. Verifying the IPAM Scopes

Figure 10. Verifying the IPAM Scopes

    In the AWS Control Tower management account, go to the CloudFormation console, click on Stacks in the navigation pane, click on Create Stack and select “With new resources” and specify this CloudFormation template to deploy a solution that provides AWS Control Tower integration with Amazon VPC IP Address Manager. In the next screen, The CloudFormation stack creation presents with the screen shown below requiring input parameters for the deployment. CloudFormation stacks are deployed using the console as explained in the documentation through console or CLI.

Figure 11. Deploying the CloudFormation Stack in the AWS Control Tower management account

Figure 11. Deploying the CloudFormation Stack in the AWS Control Tower management account.

The input parameters required are explained below

Centralized Networking resources
NetworkingAcciontid 	AWS Account ID of the networking account in your multi-account environment. Networking account holds the Amazon IPAM configuration and shares the IPAM pools with the member accounts.
Lambda Source Repository
LambdaBucket 	Name of the S3 bucket containing the Lambda package and templates. You can use default value of “ctipam-public-resources2”
LambdaPrefix 	The prefix of the S3 bucket containing the Lambda package. You can use default value of packages/”.
Other parameters
AccEnvName 	Comma separated list of evironment names for Regional IPAM pools. This parameter will used to create pools for the specific environment within a Region. Default values are Prod OU, SLDC OU. The solution expects the names of the environments to match the OU name.
AccPoolPrefixLength 	Prefix Length for Environment level IPAM Pools.
IpamPoolPrefixLength 	Prefix Length for Regional IPAM Pools.
IpamScope 	Top level IPAM  Scope for the AWS Control Tower environment.
RegionSelection 	Regions for IPAM  Sub-Pool creation.
RepoRootURL 	The full path to the S3 bucket containing the YAML resources.
TopLevelPoolCidr 	Top level pool for the IPAM in the Multi-account AWS Control Tower Environment .

    After the CloudFormation is deployed, login to the networking account and to go the VPC IP Address Manager Console to verify that the top level pool, Regional pools and Environment level pools along with the Allocation tags(Prod OU and SLDC).

Figure 12. Verifying the pools created in the Networking Account after the CloudFormation deployment.

Figure 12. Verifying the pools created in the Networking Account after the CloudFormation deployment.

    Under the top level pool (ipam-pool-0e37f71bc40741216), 2 Regional pools are created in us-west-2 (ipam-pool-0027f2d7cec2a6474) and us-east-1 (ipam-pool-0ae80c2062300cbf8). Under each Region, you will find 2 Environmental pools created.
    Environment pools (ipam-pool-0284d5e9f938354d9 and ipam-pool-0da932e60b3d5deb0) in Region us-west-2 and Environment pools (ipam-pool-069a9bbceeb3b2ba7 and ipam-pool-0c333d93e55f5f922 ) in us-east-1.
    You can verify the Allocation tag of each Environment Pool. Click on the Environment pool and go to the compliancy tab. Under the Resource tag compliancy section, verify the allocation tag.

Figure 13. Verifying the Allocation tag of each Environment Pool.

Figure 13. Verifying the Allocation tag of each Environment Pool.
Testing the Solution

    You can test the solution by creating a new member account using AWS Control Tower account factory in one of the OUs. Make sure you create the account under an OU which maps to a particular environment. Select the Organizational unit for the member account : Prod OU or SDLC OU.

Figure 14. Creating new member Account using Control Tower Account Factory.

Figure 14. Creating new member Account using Control Tower Account Factory.

    The example here shows an account CTTEST created under Prod OU.

Figure 15. Verify the new member Account is created under AWS Control Tower

Figure 15. Verify the new member Account is created under AWS Control Tower

    Once the member account is created, you can login into to the member account. Go to the Amazon VPC IP Address Manager console, and select Pools. This will show you the list of IPAM pools that match the allocation tag with the member account’s OU name.

Figure 16. Verify the IPAM Pools shared with the new member Account in the Amazon VPC IP Address Manager.

Figure 16. Verify the IPAM Pools shared with the new member Account in the Amazon VPC IP Address Manager.

    You can verify the Allocation tag of each shared Environment Pool to check whether it matches the OU name of the member account. Click on the shared Environment pool and go to the compliancy tab. Under the Resource tag compliancy section, verify the allocation tag.
    The allocation tag matches the Organization unit name which in this case is Prod OU.

Figure 17. Verify the Allocation tag of each shared Environment Pool in IPAM Pools shared with the new member Account.

Figure 17. Verify the Allocation tag of each shared Environment Pool in IPAM Pools shared with the new member Account.
Figure 18. Verify the Allocation tag of each shared Environment Pool in IPAM Pools shared with the new member Account.

Figure 18. Verify the Allocation tag of each shared Environment Pool in IPAM Pools shared with the new member Account.

    Additionally, you can go the Resource Access Manager in the member account to confirm the pools shared with the member account. From the resource share, you can verify the Owner of the share which is the AWS Control Tower management account.

Figure 19. Verify the IPAM Pools shared with the new member Account in the Amazon Resource Access Manager.

Figure 19. Verify the IPAM Pools shared with the new member Account in the Amazon Resource Access Manager.

    In the member account, Now go the VPC console and try creating VPC in one of the Regions specified in the CloudFormation template. You would now be able to select the IPAM-allocated IPv4 CIDR block.

Figure 20. Creating VPC in the new member account and verifying that the IPAM pools are shared.

Figure 20. Creating VPC in the new member account and verifying that the IPAM pools are shared.
Cleanup

Follow these steps to remove the resources deployed by this solution. These steps will remove the VPCs created by this solution.

    In the member accounts, remove any VPC that are using IPAM assigned IP addresses.
    In the networking account, de-provision the CIDR blocks provisioned to the IPAM pools
    In the networking account, delete the CloudFormation stack with name starting with StackSet-CTNetworkingStackSet- that was deployed as part of this solution.
    In the AWS Control Tower management account, delete the main CloudFormation stack that was deployed for this solution.

Considerations

Keep in mind the following considerations with respect to this solution.

    While the solution shares environment pools from all Regions to the member account, user can only use the environment pool from a particular Region where the VPC is being created.
    The solution presented here covers the scenario of private IP addressing within your environment. This can be modified to support your IPAM pool plan requirements for public IP addressing. Refer to this tutorial to see how you can use your own public IP space with IPAM.
    While this solution implements a IPAM pool hierarchy based on environment, customers can choose to implement their own IPAM hierarchy based on their needs. Refer to other example IPAM pool plans.
    While the solution will allow for creating summarized prefixes in route tables and security groups, as your environment scales you may still have large number of entries to connect your evolving networks. Consider using Managed Prefix lists to simplify route table and security group configurations.
    You are charged hourly for each active IP address that IPAM monitors. An active IP address is defined as an IP address assigned to a resource such as an EC2 instance or an Elastic Network Interface (ENI). Refer to IPAM pricing

Summary

This blog presented an approach to integrating Amazon IPAM with a multi-account environment of AWS Control Tower. As your environment scales and your teams create new accounts, this solution will help you to define only the right set of IPAM pools will be shared with those accounts. This reduces the manual effort required by network administrators to perform pool allocations and manage IP addressing. It allows the development teams to be more agile by taking away the request approval workflow and effort in ensuring unique IP block allocations. This automation helps organizations to extend the AWS Control Tower benefits of governance and business agility to networking and IP address management.
## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

