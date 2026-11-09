from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    PredictionResponse,
)
from app.services.analyze import (
    get_active_model,
    get_comparison_model,
    persist_text_analysis,
)
from app.services.auth import get_current_user

router = APIRouter(
    tags=["analyze"],
)

from app.ml.registry import (
    clean_text,
    get_available_model_ids,
    get_predictor,
)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
)
def analyze_text(
    data: AnalyzeRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Retrieve the active model
    try:
        active_model = get_active_model(db)
        models_to_use = [active_model]

        predictors_to_use = [
            (model, get_predictor(model.model_id)) for model in models_to_use
        ]
        cleaned_text = clean_text(data.text)

        if data.compare:
            comparison_model = get_comparison_model(
                db,
                active_model.model_id,
                get_available_model_ids(),
            )

            if comparison_model is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No second registered model is available for comparison",
                )

            models_to_use.append(comparison_model)
            predictors_to_use.append(
                (comparison_model, get_predictor(comparison_model.model_id))
            )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Run prediction
    prediction_data = []
    response_results = []

    for model, predictor in predictors_to_use:
        results = predictor.predict([cleaned_text])

        if len(results) != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The predictor returned an unexpected number of results",
            )

        prediction = results[0]
        probabilities = prediction.probabilities

        prediction_data.append(
            {
                "model_id": model.model_id,
                "label": prediction.label,
                "confidence": prediction.confidence,
                "prob_positive": probabilities["positive"],
                "prob_neutral": probabilities["neutral"],
                "prob_negative": probabilities["negative"],
            }
        )

        response_results.append(
            PredictionResponse(
                model=model.name,
                label=prediction.label,
                confidence=prediction.confidence,
                probabilities=probabilities,
            )
        )

    query = persist_text_analysis(
        db,
        user_id=current_user.user_id,
        text=data.text,
        cleaned_text=cleaned_text,
        predictions=prediction_data,
        primary_model_id=active_model.model_id,
    )

    return AnalyzeResponse(
        query_id=query.query_id,
        results=response_results,
    )
