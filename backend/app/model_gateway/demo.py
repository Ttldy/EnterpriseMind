from app.model_gateway.contracts import (
    ModelRequest,
    ModelResponse,
)


class DemoProvider:
    def __init__(
        self,
        model: str = "demo-model",
    ) -> None:
        self._model = model

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        return ModelResponse(
            text=(f"【{self._model}】" f"{request.user_message}"),
            model=self._model,
        )
