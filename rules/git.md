# On start

1. Initialize git mono repository in root folder (for the set of services) if it's not initialized yet
2. Create gitignore and ignore everything except source code
3. Using github-mcp create private repository in github and connect in to this project

# Always

1. Work in develop branch as default
2. Don't commit or push anything if user doesn't ask for it
3. Check that gitignore file has enough masks

# On each task when user said to push

1. Commit and push it to "develop" branch and create a Pull request to main branch
2. Return link to the pull request to the user
