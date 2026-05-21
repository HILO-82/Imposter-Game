"""Train and save KNN and Logistic Regression models."""

from ml.vote_bot import train_and_save as train_lr
from ml.word_bot import train_and_save as train_knn


def main():
    print("Training KNN word model...")
    train_knn()
    print("Saved knn_model.pkl")
    print("Training Logistic Regression vote model...")
    train_lr()
    print("Saved lr_model.pkl")


if __name__ == "__main__":
    main()
