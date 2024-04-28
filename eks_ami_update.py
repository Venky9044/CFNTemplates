import boto3
from tabulate import tabulate
from datetime import date

class EKS_utils():
    # Config boto3 session/client
    def __init__(self, region_name: str):
        try:
            self.client = boto3.client('eks', region_name=region_name)
            self.ec2_client = boto3.client('ec2', region_name=region_name)
            self.asg_client = boto3.client('autoscaling', region_name=region_name)
            self.region_name = region_name
            print("Connected to " + region_name + ".\n")
        except Exception as e:
            print(e)

    # Get selected cluster version
    def describe_cluster(self, cluster_name):
        print("Cluster information")
        try:
            response = self.client.describe_cluster(name=cluster_name)
        except Exception as e:
            print("Cluster " + cluster_name + " not found in region " + self.region_name +
                  ". \nPlease check the region and cluster to proceed further...")
            exit(0)
        cluster_info = response.get('cluster')
        self.cluster_version = cluster_info.get('version')
        self.cluster_status = cluster_info.get('status')
        self.cluster_platformVersion = cluster_info.get('platformVersion')
        print(cluster_name
              + "\n\tVersion : " + self.cluster_version
              + "\n\tStatus : " + self.cluster_status
              + "\n\tPlatform Version : " + self.cluster_platformVersion
              )

    def get_autoscaling_group(self, cluster_name: str):
        self.cluster_name = cluster_name

        self.describe_cluster(cluster_name=cluster_name)

        response = self.client.list_nodegroups(clusterName=cluster_name)
        node_groups_for_autoscaling = response.get('nodegroups')
        node_groups_asg = []
        for asg in node_groups_for_autoscaling:
            response = self.client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=asg
            )
            asg_details = response.get['nodegroup']['resources']['autoScalingGroups'][0]['name']
            node_groups_asg.append(asg_details)
            print(node_groups_asg)


    # Identify the ami_id being used currently
    def get_ami_id(self, cluster_name: str):
        self.cluster_name = cluster_name

        # Get cluster_version
        self.describe_cluster(cluster_name=cluster_name)

        # List the nodes/nodegroups
        print("\nNode groups and AMIs of " + cluster_name + " cluster")
        response = self.client.list_nodegroups(clusterName=cluster_name)
        node_groups = response.get('nodegroups')
        ng_list = []
        for ng in node_groups:
            # list the version which includes ami id
            response = self.client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng
            )
            ng_describe = response.get('nodegroup')
            ng_name = ng_describe.get('nodegroupName')
            ng_version = ng_describe.get('releaseVersion')
            ng_list.append(ng_version)
            print(ng_name + " : " + ng_version)

        ng_set = set(ng_list)
        if len(ng_set) > 1:
            print("\nMismatching AMI ids in node groups for cluster " + cluster_name)
            print(str(ng_list))
            exit(0)
        else:
            print("\nAll AMI ids in different node groups are matching")
            print(ng_set.pop())
            self.verify_ami_presence(ng_list)
        

    def verify_ami_presence(self, ami_id: list):
        print("\nChecking if current AMI exists in the AMI repository")
        # Check if ami_id is present in AWS AMIS list
        try:
            response = self.ec2_client.describe_images(
                ImageIds=ami_id
            )
            print("AMI ID " + ami_id[0] + " found.")
            print("Details:")
            img_data = response.get('Images')[0]
            self.days_diff = self.calculate_days(img_data.get('CreationDate'))
            print(img_data.get('ImageId') + " : " + img_data.get('CreationDate') + " : " + str(self.days_diff) + " days")
        except Exception as e:
            print("AMI ID " + ami_id[0] + " Not found.\n", e)

    def calculate_days(self, cdate):
        # Format date for conversion
        date_split = cdate.split('T')[0].split('-')
        p_date = date(int(date_split[0]), int(date_split[1]), int(date_split[2]))
        c_date = date.today()
        delta = c_date - p_date
        return delta.days

    def check_for_new_ami(self):
        # List and filter all amis based on AMI NAME
        image_name = 'sc-issuing-eks-linux-' + self.cluster_version + '*'
        response = self.ec2_client.describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': [
                        image_name,
                    ]
                },
            ]
        )

        mydata = []
        for img in response.get('Images'):
            mydata.append([img.get('ImageId'), img.get('CreationDate'), self.calculate_days(img.get('CreationDate'))])
            mydata.sort(key=lambda mydata: mydata[2])

        # create header
        head = ["Image ID", "Creation date", "Days Old"]

        # display table
        print(tabulate(mydata, headers=head))

        print("\nComparing existing image with the latest image")
        # compare the latest image from the above list of images pulled from AMI repo
        if self.days_diff == mydata[0][2]:
            print("Latest image already being used by cluster " + self.cluster_name)
            print("Image details:\n"
                  + "\tImage ID : " + mydata[0][0]
                  + "\n\tCreation date : " + mydata[0][1]
                  )
        else:
            print("Cluster " + self.cluster_name + " is using an older image.")
            latest_ami_id = mydata[0][0]
            print("Latest available image ID for EKS " + self.cluster_version + ": " + latest_ami_id)
            return latest_ami_id

if __name__ == "__main__":
    provided_region = "us-east-1"
    provided_cluster = "tls-mrcdev-use1" 

    eks_utils = EKS_utils(region_name=provided_region)

    eks_utils.describe_cluster(cluster_name=provided_cluster)

    eks_utils.get_ami_id(cluster_name=provided_cluster)

    eks_utils.check_for_new_ami()
