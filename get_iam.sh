#!/bin/bash

STACK_LIST_FILE="output.txt"

stack_names=$(cat $STACK_LIST_FILE)

for stack_name in $stack_names; do
    echo "Stack: $stack_name"

    iam_roles=$(aws cloudformation describe-stack-resources --stack-name $stack_name --query "StackResources[?ResourceType=='AWS::IAM::Role'].PhysicalResourceId" --output text)

    if [ -z "$iam_roles" ]; then
        echo "No IAM roles found in the stack."
    else
        echo "IAM Roles:"
        echo $iam_roles >> roles.txt
    fi

    echo "----------------------------------"
done



