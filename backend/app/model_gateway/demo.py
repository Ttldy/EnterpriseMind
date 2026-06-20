from app.model_gateway.contracts import ModelRequest, ModelResponse


class DemoProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            text=f"【演示模型】{request.user_message}",
            model="demo-model",
        )
