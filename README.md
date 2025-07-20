# function-python-composite

A Crossplane composition function that lets you compose Composites using python.

Provide a Python script that implements a Composite class that implements
a compose method.

```python
class Composite(BaseComposite):
  def compose(self):
```

The `function-python-composite` BaseComposite class provides the following fields:

| Field | Description |
| ----- | ----------- |
| self.context | The composition context |
| self.environment | The composition environment |
| self.extras | Access to extra resources |
| self.credentials | Access to the composite's credentials |
| self.apiVersion | The composite apiVersion |
| self.kind | The composite kind |
| self.metadata | The composite metadata |
| self.spec | The composite spec |
| self.resources | The composite manageed resources |
| self.status | The composite status |
| self.conditions | The composite conditions |
| self.connection | The composite connection details |
| self.ready | The composite ready state |
| self.logger | A logger to emit log messages in the function pod's log |

Creating and accessing resources using `self.resources` returns a python
object with the following fields:

| Field | Description |
| ----- | ----------- |
| resource.name | The managed resource name within the composite |
| resource.apiVersion | The resource apiVersion |
| resource.kind | The resource kind |
| resource.externalName | The resource external name |
| resource.metadata | The resource metadata |
| resource.spec | The resource spec |
| resource.status | The resource status |
| resource.conditions | The resource conditions |
| resource.connection | The resource connection details |
| resource.ready | The resource ready state |

The following example creates an AWS S3 Bucket:

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: compose-a-resource-with-python
spec:
  compositeTypeRef:
    apiVersion: example.crossplane.io/v1
    kind: XR
  mode: Pipeline
  pipeline:
  - step: compose-a-resource-with-python
    functionRef:
      name: function-python-composite
    input:
      apiVersion: python.fn.crossplane.io/v1beta1
      kind: Composite
      composite: |
        class Composite(BaseComposite):
          def compose(self):
            resource = self.resources.bucket('s3.aws.upbound.io/v1beta2', 'Bucekt')
            resource.spec.forProvider.region = self.spec.region
            resource.ready = True
```

In the `example` directory are most of the function-go-template examples implemented
using function-python-composite. In addition, the eks-cluster example is a complex
example composing many resources.

[function-sdk-python]: https://github.com/crossplane/function-sdk-python
[buf-types]: https://buf.build/crossplane/crossplane/docs/main:apiextensions.fn.proto.v1
[python-protobuf]: https://protobuf.dev/reference/python/python-generated/
[function-template-python]: https://github.com/crossplane/function-template-python
