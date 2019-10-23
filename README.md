# -⚡Levin⚡-

Fast and scalable framework to build application like you want with http2 native support

This Framework based on simple principle:  "Divide and conquer"

## Intro
Handlers are the basis of any modern framework. How they are used and how framework provides the API to determine them affects the success of the framework.
Levin makes it possible to influence the api handlers and modify the framework

### Components
The Application are determined by components and control livecycle of this components.
Component have customizable options (settings), middleware, can path request object, inject their own api to the application,  and provide management commands
Live cycle:

Application create -> component init -> component configure -> app start -> component start -> app handle request -> component middleware -> app stop -> component stop
component init -> component configure -> component start -> component handle request -> component stop

```python
class Component:
    name: str
     
    def init(self, app):
        ...

    (async )def start(self, app):
        ...

    (async )def stop(self, app):
        ...

    async def middleware(self, request, handler, call_next):
        ...
        response = await call_next(request, handler)  # ordinary behavior
        ...
        return response
```

Each component have uniq name and default configure parameter -  `enable` as `True`. Every class attribute is considered as configurable parameter and can be redefined before application start
```python
app.configure({
    "templates": {
        "path": "/",
        "enable": False,
    },
    "json_format": {
        "json_dumps": ujson.dumps,
        "default": None,
    },
    "process_executor": {
        "max_workers": 1
    },
})

```

### Default components
There are a few components to provide base features:
* `logger` - Log responses 
* `patch_request` - Add base attributes to request object  -`content_type`, `encoding`, `query_params`, `json`, `path` 
* `handler_timeout` - Limit time execution of handlers  
* `handle_error` - handle errors  
* `sync_to_async`, `process_executor` - makes it possible to run handlers in process or thread pool - allow use sync functions without blocking loop  
* `json_format`, `templates` - provide simple api to use templates/json in handlers 
* `profile` - auto profile for handlers (detect long running handlers and trace time execution and memory usage of it) 
* `route` - for routing
* `cli` - api to create management commands


# Components methods , middleware , commands  


Example:
```python
from levin import app

app.configure({
    "cache": {
        "client": redis,
    }
})

@app.route.get("/", name="root", status=201)
async def root(request):
    return {"status": await app.cache.status}

@app.route.post("/", name="root", status=201)
def post(request):
    return {"q": request.query_params, **request.json}



if __name__ == '__main__':
    app.cli()

```


##Features
* ⚡⚡⚡
* HTTP2 base 
* Divide-and-conquer
* Easy run at background 
* build you own framework

Todo: 
* logging
* import ++  proxy  object
* client ip and proxy info
* asgi support
* Push messages

C0MPONENTS
* Metrics
* validation
* docs ?
* HTTP caching in box 
* Languages
* cookies
* session
* db integraton + simple admin
* rate  limit
