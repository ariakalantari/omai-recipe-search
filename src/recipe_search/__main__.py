import uvicorn

if __name__ == "__main__":
    # The public bind is required inside Docker; host exposure is controlled by the runtime.
    uvicorn.run(
        "recipe_search.main:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=False,
    )
