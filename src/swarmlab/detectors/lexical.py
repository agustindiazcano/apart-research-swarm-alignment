"""D1 lexical detector combining TF-IDF, dense stylistic features, and Platt scaling."""
from __future__ import annotations

import math
import re
from collections.abc import Sequence
from pathlib import Path

import joblib
import numpy as np
import scipy.sparse
from sklearn.calibration import _SigmoidCalibration
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MaxAbsScaler

from swarmlab.schema import DetectorContext, MessageView

CODE_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{4,}\b"
)
DIGIT_PATTERN: re.Pattern[str] = re.compile(r"\d")


def extract_dense_features(texts: Sequence[str]) -> np.ndarray:
    """Extract vocabulary-independent dense features for a sequence of texts."""
    features = np.zeros((len(texts), 4), dtype=np.float64)
    for i, text in enumerate(texts):
        length = len(text)
        features[i, 0] = math.log1p(length)
        features[i, 1] = (text.count("?") / length) if length > 0 else 0.0
        features[i, 2] = float(len(CODE_TOKEN_PATTERN.findall(text)))
        features[i, 3] = float(len(DIGIT_PATTERN.findall(text)))
    return features


class LexicalDetector:
    """D1 lexical detector using logistic regression with Platt scaling."""

    name: str = "d1"

    def __init__(self, seed: int = 0, c: float = 1.0) -> None:
        self.seed = seed
        self.c = c
        self._vectorizer: TfidfVectorizer | None = None
        self._scaler: MaxAbsScaler | None = None
        self._classifier: LogisticRegression | None = None
        self._calibrator: _SigmoidCalibration | None = None

    def fit(self, texts: Sequence[str], labels: Sequence[int]) -> LexicalDetector:
        """Fit TF-IDF, dense features, logistic regression, and Platt scaling.

        If either class has fewer than 5 examples, calibration is fitted on the full
        training data instead of a held-out split.
        """
        if len(texts) != len(labels):
            raise ValueError("texts and labels must have equal length")
        if len(texts) == 0:
            raise ValueError("texts and labels must not be empty")

        labels_arr = np.asarray(labels, dtype=int)
        unique_classes = np.unique(labels_arr)
        if len(unique_classes) < 2:
            raise ValueError("fit requires at least two distinct classes")

        counts = {int(c): int(np.sum(labels_arr == c)) for c in unique_classes}
        min_class_count = min(counts.values())

        if min_class_count < 5:
            train_texts = list(texts)
            train_labels = list(labels)
            calib_texts = train_texts
            calib_labels = train_labels
        else:
            train_idx, calib_idx = train_test_split(
                np.arange(len(texts)),
                test_size=0.2,
                stratify=labels_arr,
                random_state=self.seed,
            )
            train_texts = [texts[i] for i in train_idx]
            train_labels = [int(labels_arr[i]) for i in train_idx]
            calib_texts = [texts[i] for i in calib_idx]
            calib_labels = [int(labels_arr[i]) for i in calib_idx]

        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True, stop_words=None)
        tfidf_train = self._vectorizer.fit_transform(train_texts)

        dense_train = extract_dense_features(train_texts)
        self._scaler = MaxAbsScaler()
        scaled_dense_train = self._scaler.fit_transform(dense_train)

        x_train = scipy.sparse.hstack(
            [tfidf_train, scipy.sparse.csr_matrix(scaled_dense_train)], format="csr"
        )

        self._classifier = LogisticRegression(
            C=self.c,
            random_state=self.seed,
            max_iter=1000,
        )
        self._classifier.fit(x_train, train_labels)

        tfidf_calib = self._vectorizer.transform(calib_texts)
        dense_calib = extract_dense_features(calib_texts)
        scaled_dense_calib = self._scaler.transform(dense_calib)
        x_calib = scipy.sparse.hstack(
            [tfidf_calib, scipy.sparse.csr_matrix(scaled_dense_calib)], format="csr"
        )
        calib_decision = self._classifier.decision_function(x_calib)

        self._calibrator = _SigmoidCalibration()
        self._calibrator.fit(calib_decision, calib_labels)

        return self

    def scores(self, texts: Sequence[str]) -> list[float]:
        """Compute calibrated probabilities in [0, 1] for a sequence of texts."""
        if (
            self._vectorizer is None
            or self._scaler is None
            or self._classifier is None
            or self._calibrator is None
        ):
            raise RuntimeError("LexicalDetector is not fitted")

        if len(texts) == 0:
            return []

        tfidf = self._vectorizer.transform(texts)
        dense = extract_dense_features(texts)
        scaled_dense = self._scaler.transform(dense)
        x = scipy.sparse.hstack(
            [tfidf, scipy.sparse.csr_matrix(scaled_dense)], format="csr"
        )
        decision = self._classifier.decision_function(x)
        raw_probs = self._calibrator.predict(decision)
        clipped_probs = np.clip(raw_probs, 0.0, 1.0)
        return [float(p) for p in clipped_probs]

    def score_text(self, text: str) -> float:
        """Score a single text string returning calibrated probability in [0, 1]."""
        return self.scores([text])[0]

    def score(self, message: MessageView, context: DetectorContext) -> float:
        """Score a message using only message.text."""
        return self.score_text(message.text)

    def save(self, path: Path) -> None:
        """Save fitted detector to disk using joblib."""
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> LexicalDetector:
        """Load detector from disk using joblib."""
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError(f"Loaded object is not {cls.__name__}")
        return loaded
