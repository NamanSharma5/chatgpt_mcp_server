# ChatGPT Memory MCP Server
*Under MIT License*

Since ChatGPT has memory it becomes a valuable data source for other models; I'm facilitating a shared memory outside of a single model provider.

To use this MCP server:
1. Clone the repository
2. Install the required packages using `pip install -r requirements.txt`
3. Set up the environment variables
    - You can use the path to your Chrome executable (find this by typing `chrome://version` in the address bar of Chrome) or set it to `None` to use the default path.
4. Link the server with an application, for example with Claude Desktop App, follow instructions here: https://modelcontextprotocol.io/quickstart/server#testing-your-server-with-claude-for-desktop
    - Here is an example Claude config file:
    ```
    {
        "mcpServers": {
        "chatgpt_memory": {
            "command": "C:\path_to_where_you_cloned_this_repo\\.venv\\Scripts\\python.exe",
            "args": [
                "C:\path_to_where_you_cloned_this_repo\\ChatGPT_MCPserver.py"
            ]
            }
        }
    }
    ```