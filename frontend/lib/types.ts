export interface Movie {
  id: number;
  tmdb_id: number;
  title: string;
  year: number | null;
  runtime: number | null;
  genres: string[];
  directors: string[];
  cast_members: string[];
  overview: string | null;
  poster_url: string | null;
  tagline: string | null;
  backdrop_url: string | null;
  vote_average: number | null;
  vote_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface MovieSearchResult {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_url: string | null;
}

export interface MovieReview {
  reviewer_name: string;
  reviewer_picture_url: string | null;
  rating: number | null;
  liked: boolean;
  review_text: string;
  watched_date: string;
}

export interface DiaryEntry {
  id: number;
  movie: Movie;
  watched_date: string;
  rating: number | null;
  rewatch: boolean;
  review_text: string | null;
  tags: string[];
  liked: boolean;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface WatchlistItem {
  id: number;
  movie: Movie;
  added_date: string;
}

export interface MovieList {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListMovieItem {
  movie: Movie;
  position: number;
}

export interface MovieListDetail extends MovieList {
  items: ListMovieItem[];
}

export interface CurrentUser {
  email: string;
  display_name: string;
  profile_picture_url: string | null;
  created_at: string;
}
