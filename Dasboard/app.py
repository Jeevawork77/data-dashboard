import os
import uuid

import pandas as pd
import plotly.express as px
from flask import Flask, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED = {".csv", ".xlsx"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB limit


def load_and_clean(path):
    """Step 3: Pandas - read the file and clean it."""
    ext = os.path.splitext(path)[1].lower()
    df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df.drop_duplicates().reset_index(drop=True)
    return df


def build_charts(df):
    """Step 3: Plotly - generate charts on the backend."""
    charts = []
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = [
        c for c in df.columns
        if c not in num_cols and 1 < df[c].nunique() <= 20
    ]

    def to_html(fig):
        fig.update_layout(margin=dict(l=30, r=20, t=50, b=30), height=380)
        return fig.to_html(full_html=False, include_plotlyjs=False)

    if cat_cols and num_cols:
        cat, num = cat_cols[0], num_cols[0]
        grouped = df.groupby(cat, as_index=False)[num].sum()
        charts.append(("Bar Chart", to_html(
            px.bar(grouped, x=cat, y=num, title=f"{num} by {cat}"))))
        charts.append(("Pie Chart", to_html(
            px.pie(grouped, names=cat, values=num, title=f"{num} share by {cat}"))))

    if num_cols:
        x = df.index if len(num_cols) == 1 else num_cols[0]
        y = num_cols[0] if len(num_cols) == 1 else num_cols[1]
        charts.append(("Line Graph", to_html(
            px.line(df, x=x, y=y, title=f"{y} trend"))))

    return charts


@app.route("/")
def index():
    return render_template("index.html", result=None, error=None)


@app.route("/upload", methods=["POST"])
def upload():
    """Step 2: receive the uploaded file and save it in the backend folder."""
    file = request.files.get("file")
    if not file or file.filename == "":
        return render_template("index.html", result=None, error="File select pannunga."), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED:
        return render_template("index.html", result=None,
                               error="Only .csv or .xlsx files mattum allowed."), 400

    saved = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    file.save(saved)

    try:
        df = load_and_clean(saved)
    except Exception as exc:
        return render_template("index.html", result=None,
                               error=f"File read panna mudiyala: {exc}"), 400

    result = {
        "filename": file.filename,
        "rows": len(df),
        "cols": len(df.columns),
        "charts": build_charts(df),
        "table": df.head(50).to_html(classes="data-table", index=False, border=0),
        "summary": df.describe().round(2).to_html(classes="data-table", border=0)
        if not df.select_dtypes(include="number").empty else "",
    }
    # Step 4: send generated charts + clean rows back to the HTML page
    return render_template("index.html", result=result, error=None)


if __name__ == "__main__":
    app.run(debug=True)
