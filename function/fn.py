"""A Crossplane composition function."""

import asyncio
import datetime
import inspect

import grpc
import crossplane.function.logging
import crossplane.function.response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1

import function.composite


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.logger = crossplane.function.logging.get_logger()
        self.modules = {}

    async def RunFunction(
        self, request: fnv1.RunFunctionRequest, _: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        """Run the function."""
        composite = request.observed.composite.resource
        logger = self.logger.bind(
            apiVersion=composite['apiVersion'],
            kind=composite['kind'],
            name=composite['metadata']['name'],
        )
        if request.meta.tag:
            logger = logger.bind(tag=request.meta.tag)
        input = request.input
        if 'step' in input:
            logger = logger.bind(step=input['step'])
        ttl = crossplane.function.response.DEFAULT_TTL
        if 'ttl' in input:
            ttl = input['ttl']
            try:
                ttl = datetime.timedelta(seconds=int(ttl))
            except ValueError:
                try:
                    ttl = [*map(int, ttl.split(':'))]
                    if len(ttl) == 1:
                        ttl = datetime.timedelta(seconds=ttl[0])
                    elif len(ttl) == 2:
                        ttl = datetime.timedelta(minutes=ttl[0], seconds=ttl[1])
                    elif len(ttl) == 3:
                        ttl = datetime.timedelta(hours=ttl[0], minutes=ttl[1], seconds=ttl[2])
                except ValueError:
                    pass
        logger.debug(f"Running, ttl: {ttl}")
        response = crossplane.function.response.to(request, ttl)

        if 'composite' not in input:
            logger.error('Missing "composite" input')
            crossplane.function.response.fatal(response, 'Missing "composite" input')
            return response
        composite = input['composite']

        module = self.modules.get(composite)
        if not module:
            module = Module()
            try:
                exec(composite, module.__dict__)
            except Exception as e:
                crossplane.function.response.fatal(response, f"Exec exception: {e}")
                logger.exception('Exec exception')
                return response
            if not hasattr(module, 'Composite') or not inspect.isclass(module.Composite):
                logger.error('Composite did not define "class Composite"')
                crossplane.function.response.fatal(response, 'Function did not define "class Composite')
                return response
            self.modules[composite] = module

        try:
            composite = module.Composite(request, response, logger)
            result = composite.compose()
            if asyncio.iscoroutine(result):
                await result
            if composite.request.input['auto-ready'] != False:
                for name, resource in composite.resources:
                    if resource.ready is None:
                        if resource.conditions.Ready.status:
                            resource.ready = True
        except Exception as e:
            crossplane.function.response.fatal(response, f"Run exception: {e}")
            logger.exception('Run exception')
            return response
        logger.debug('Returning')
        return response


class Module:
    def __init__(self):
        self.BaseComposite = function.composite.BaseComposite
