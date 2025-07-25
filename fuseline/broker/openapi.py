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
                    "description": "List of workflow schemas this worker can run",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/WorkerRegistration"},
                            "examples": {
                                "default": {
                                    "summary": "Example payload",
                                    "value": {
                                        "workflows": [
                                            {
                                                "workflow_id": "example",
                                                "version": "1",
                                                "steps": {},
                                                "outputs": []
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "Worker ID"}},
            }
        },
        "/repository/register": {
            "post": {
                "summary": "Register repository",
                "tags": ["repository"],
                "requestBody": {
                    "description": "Repository metadata",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RepositoryInfo"},
                            "examples": {
                                "default": {
                                    "summary": "Example payload",
                                    "value": {
                                        "name": "my-repo",
                                        "url": "https://github.com/example/workflows.git",
                                        "workflows": ["package.module:workflow"],
                                        "credentials": {"token": "<PAT>", "username": "gituser"}
                                    }
                                }
                            }
                        }
                    }
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
                "requestBody": {
                    "description": "Workflow schema and optional inputs",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DispatchRequest"},
                            "examples": {
                                "default": {
                                    "summary": "Example payload",
                                    "value": {
                                        "workflow": {
                                            "workflow_id": "example",
                                            "version": "1",
                                            "steps": {},
                                            "outputs": []
                                        },
                                        "inputs": {}
                                    }
                                }
                            }
                        }
                    }
                },
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
                "requestBody": {
                    "description": "Step state and optional result",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/StepReport"},
                            "examples": {
                                "default": {
                                    "summary": "Example payload",
                                    "value": {
                                        "workflow_id": "wf",
                                        "instance_id": "abc",
                                        "step_name": "build",
                                        "state": "SUCCEEDED",
                                        "result": None
                                    }
                                }
                            }
                        }
                    }
                },
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
                    "credentials": {"$ref": "#/components/schemas/RepositoryCredentials"},
                },
                "required": ["name", "url", "workflows"],
                "example": {
                    "name": "my-repo",
                    "url": "https://github.com/example/workflows.git",
                    "workflows": ["package.module:workflow"],
                    "credentials": {"token": "<PAT>", "username": "gituser"},
                },
            },
            "WorkflowSchema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "version": {"type": "string"},
                    "steps": {"type": "object"},
                    "outputs": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "policies": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                },
                "required": ["workflow_id", "version", "steps", "outputs"],
                "example": {
                    "workflow_id": "example",
                    "version": "1",
                    "steps": {},
                    "outputs": []
                },
            },
            "WorkerRegistration": {
                "type": "object",
                "properties": {
                    "workflows": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/WorkflowSchema"},
                    }
                },
                "required": ["workflows"],
                "example": {
                    "workflows": [
                        {
                            "workflow_id": "example",
                            "version": "1",
                            "steps": {},
                            "outputs": []
                        }
                    ]
                },
            },
            "DispatchRequest": {
                "type": "object",
                "properties": {
                    "workflow": {"$ref": "#/components/schemas/WorkflowSchema"},
                    "inputs": {"type": "object"},
                },
                "required": ["workflow"],
                "example": {
                    "workflow": {
                        "workflow_id": "example",
                        "version": "1",
                        "steps": {},
                        "outputs": []
                    },
                    "inputs": {}
                },
            },
            "StepReport": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"},
                    "instance_id": {"type": "string"},
                    "step_name": {"type": "string"},
                    "state": {"type": "string"},
                    "result": {},
                },
                "required": ["workflow_id", "instance_id", "step_name", "state", "result"],
                "example": {
                    "workflow_id": "wf",
                    "instance_id": "abc",
                    "step_name": "build",
                    "state": "SUCCEEDED",
                    "result": None
                },
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
