from __future__ import annotations

"""OpenAPI specification for the Fuseline HTTP broker."""

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Fuseline Broker API", "version": "1.0"},
    "tags": [
        {"name": "repository", "description": "Manage workflow repositories"},
        {"name": "worker", "description": "Register and monitor workers"},
        {"name": "workflow", "description": "Dispatch and run workflows"},
        {"name": "system", "description": "Broker metadata"},
    ],
    "paths": {
        "/worker/register": {
            "post": {
                "summary": "Register worker",
                "tags": ["worker"],
                "requestBody": {
                    "content": {"application/json": {"schema": {"type": "array", "items": {"type": "object"}}}}
                },
                "responses": {"200": {"description": "Worker ID"}},
            }
        },
        "/repository/register": {
            "post": {
                "summary": "Register repository",
                "tags": ["repository"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RepositoryInfo"}
                        }
                    },
                },
                "responses": {"204": {"description": "OK"}},
            }
        },
        "/repository": {
            "get": {
                "summary": "List or fetch repository info",
                "tags": ["repository"],
                "parameters": [
                    {"name": "name", "in": "query", "required": False, "schema": {"type": "string"}},
                    {"name": "page", "in": "query", "required": False, "schema": {"type": "integer"}},
                    {"name": "page_size", "in": "query", "required": False, "schema": {"type": "integer"}},
                ],
                "responses": {
                    "200": {"description": "Repository or list"},
                    "404": {"description": "Not found"},
                },
            }
        },
        "/workflow/dispatch": {
            "post": {
                "summary": "Dispatch workflow",
                "tags": ["workflow"],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "Instance ID"}},
            }
        },
        "/workflow/step": {
            "get": {
                "summary": "Get next step",
                "tags": ["workflow"],
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Step assignment"}, "204": {"description": "No step"}},
            },
            "post": {
                "summary": "Report step result",
                "tags": ["workflow"],
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/worker/keep-alive": {
            "post": {
                "summary": "Keep worker alive",
                "tags": ["worker"],
                "parameters": [{"name": "worker_id", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/status": {
            "get": {
                "summary": "Broker status",
                "tags": ["system"],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/workers": {
            "get": {
                "summary": "List workers",
                "tags": ["worker"],
                "responses": {
                    "200": {
                        "description": "Workers",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/WorkerInfo"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/workflows": {
            "get": {
                "summary": "List workflows",
                "tags": ["workflow"],
                "responses": {
                    "200": {
                        "description": "Workflows",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/WorkflowInfo"},
                                }
                            }
                        },
                    }
                },
            }
        },
    },
    "components": {
        "schemas": {
            "LastTask": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "instance_id": {"type": "string"},
                    "step_name": {"type": "string"},
                    "success": {"type": "boolean"},
                },
            },
            "WorkerInfo": {
                "type": "object",
                "properties": {
                    "worker_id": {"type": "string"},
                    "connected_at": {"type": "number"},
                    "last_seen": {"type": "number"},
                    "last_task": {"$ref": "#/components/schemas/LastTask"},
                },
                "required": ["worker_id", "connected_at", "last_seen"],
            },
            "WorkflowInfo": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "workflow": {"type": "string"},
                },
                "required": ["repository", "workflow"],
            },
            "RepositoryCredentials": {
                "type": "object",
                "properties": {
                    "token": {"type": "string"},
                    "username": {"type": "string"},
                },
            },
            "RepositoryInfo": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "workflows": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "credentials": {
                        "$ref": "#/components/schemas/RepositoryCredentials"
                    },
                },
                "required": ["name", "url", "workflows"],
            },
        }
    },
}

SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Fuseline Broker API</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist/swagger-ui.css\">
</head>
<body>
  <div id=\"swagger-ui\"></div>
  <script src=\"https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js\"></script>
  <script src=\"https://unpkg.com/swagger-ui-dist/swagger-ui-standalone-preset.js\"></script>
  <script>
  window.onload = function() {
    SwaggerUIBundle({
      url: '/openapi.json',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      layout: 'StandaloneLayout',
      operationsSorter: 'alpha',
      tagsSorter: 'alpha'
    });
  };
  </script>
</body>
</html>"""
