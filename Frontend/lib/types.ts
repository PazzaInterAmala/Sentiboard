// Shapes mirror the FastAPI schemas (Backend/app/schemas) and the contract in
// docs/IMPLEMENTATION_PLAN.md §6.2. Labels follow ML/sentiboard_ml/predictor.py LABELS.

export const SENTIMENTS = ["positive", "neutral", "negative"] as const;
export type Sentiment = (typeof SENTIMENTS)[number];

export type User = {
  user_id: number;
  username: string;
  email: string;
  role: "user" | "admin";
  created_at: string;
};

/** One model's output for one text (`PredictionResponse`). */
export type Prediction = {
  model: string; // models.name, e.g. "distilbert" or "baseline"
  label: Sentiment;
  confidence: number;
  probabilities: Record<Sentiment, number>;
};

export type AnalyzeResponse = { query_id: number; results: Prediction[] };

export type QueryType = "text" | "keyword" | "csv";
export type QueryStatus = "pending" | "processing" | "done" | "failed";

export type Query = {
  query_id: number;
  type: QueryType;
  keyword: string | null;
  file_name: string | null;
  params: Record<string, unknown> | null;
  status: QueryStatus;
  post_count: number | null;
  error_message: string | null;
  positive_share: number | null;
  created_at: string;
  finished_at: string | null;
};

export type Paginated<T> = { items: T[]; total: number };

export type JobAccepted = { query_id: number; status: QueryStatus };

export type TimeRange = "day" | "week" | "month" | "year" | "all";

export type Dashboard = {
  query: Query;
  split: Record<Sentiment, number>;
  counts: Record<Sentiment, number>;
  per_day: Array<{ date: string } & Record<Sentiment, number>>;
  top_words: Record<Sentiment, Array<{ word: string; count: number }>>;
};

export type PostWithPrediction = {
  post_id: number;
  text: string;
  author: string | null;
  subreddit: string | null;
  url: string | null;
  post_date: string | null;
  prediction: Prediction;
};
