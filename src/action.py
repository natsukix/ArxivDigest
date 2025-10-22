import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from datetime import date

import argparse
import yaml
from dotenv import load_dotenv
import openai
from relevancy import generate_relevance_score, process_subject_fields
from download_new_papers import get_papers
from discord_notifier import send_to_discord, send_error_to_discord
from summarizer import generate_summaries_batch

# Hackathon quality code. Don't judge too harshly.
# Feel free to submit pull requests to improve the code.

topics = {
    "Physics": "",
    "Mathematics": "math",
    "Computer Science": "cs",
    "Quantitative Biology": "q-bio",
    "Quantitative Finance": "q-fin",
    "Statistics": "stat",
    "Electrical Engineering and Systems Science": "eess",
    "Economics": "econ",
}

physics_topics = {
    "Astrophysics": "astro-ph",
    "Condensed Matter": "cond-mat",
    "General Relativity and Quantum Cosmology": "gr-qc",
    "High Energy Physics - Experiment": "hep-ex",
    "High Energy Physics - Lattice": "hep-lat",
    "High Energy Physics - Phenomenology": "hep-ph",
    "High Energy Physics - Theory": "hep-th",
    "Mathematical Physics": "math-ph",
    "Nonlinear Sciences": "nlin",
    "Nuclear Experiment": "nucl-ex",
    "Nuclear Theory": "nucl-th",
    "Physics": "physics",
    "Quantum Physics": "quant-ph",
}


# TODO: surely theres a better way
category_map = {
    "Astrophysics": [
        "Astrophysics of Galaxies",
        "Cosmology and Nongalactic Astrophysics",
        "Earth and Planetary Astrophysics",
        "High Energy Astrophysical Phenomena",
        "Instrumentation and Methods for Astrophysics",
        "Solar and Stellar Astrophysics",
    ],
    "Condensed Matter": [
        "Disordered Systems and Neural Networks",
        "Materials Science",
        "Mesoscale and Nanoscale Physics",
        "Other Condensed Matter",
        "Quantum Gases",
        "Soft Condensed Matter",
        "Statistical Mechanics",
        "Strongly Correlated Electrons",
        "Superconductivity",
    ],
    "General Relativity and Quantum Cosmology": ["None"],
    "High Energy Physics - Experiment": ["None"],
    "High Energy Physics - Lattice": ["None"],
    "High Energy Physics - Phenomenology": ["None"],
    "High Energy Physics - Theory": ["None"],
    "Mathematical Physics": ["None"],
    "Nonlinear Sciences": [
        "Adaptation and Self-Organizing Systems",
        "Cellular Automata and Lattice Gases",
        "Chaotic Dynamics",
        "Exactly Solvable and Integrable Systems",
        "Pattern Formation and Solitons",
    ],
    "Nuclear Experiment": ["None"],
    "Nuclear Theory": ["None"],
    "Physics": [
        "Accelerator Physics",
        "Applied Physics",
        "Atmospheric and Oceanic Physics",
        "Atomic and Molecular Clusters",
        "Atomic Physics",
        "Biological Physics",
        "Chemical Physics",
        "Classical Physics",
        "Computational Physics",
        "Data Analysis, Statistics and Probability",
        "Fluid Dynamics",
        "General Physics",
        "Geophysics",
        "History and Philosophy of Physics",
        "Instrumentation and Detectors",
        "Medical Physics",
        "Optics",
        "Physics and Society",
        "Physics Education",
        "Plasma Physics",
        "Popular Physics",
        "Space Physics",
    ],
    "Quantum Physics": ["None"],
    "Mathematics": [
        "Algebraic Geometry",
        "Algebraic Topology",
        "Analysis of PDEs",
        "Category Theory",
        "Classical Analysis and ODEs",
        "Combinatorics",
        "Commutative Algebra",
        "Complex Variables",
        "Differential Geometry",
        "Dynamical Systems",
        "Functional Analysis",
        "General Mathematics",
        "General Topology",
        "Geometric Topology",
        "Group Theory",
        "History and Overview",
        "Information Theory",
        "K-Theory and Homology",
        "Logic",
        "Mathematical Physics",
        "Metric Geometry",
        "Number Theory",
        "Numerical Analysis",
        "Operator Algebras",
        "Optimization and Control",
        "Probability",
        "Quantum Algebra",
        "Representation Theory",
        "Rings and Algebras",
        "Spectral Theory",
        "Statistics Theory",
        "Symplectic Geometry",
    ],
    "Computer Science": [
        "Artificial Intelligence",
        "Computation and Language",
        "Computational Complexity",
        "Computational Engineering, Finance, and Science",
        "Computational Geometry",
        "Computer Science and Game Theory",
        "Computer Vision and Pattern Recognition",
        "Computers and Society",
        "Cryptography and Security",
        "Data Structures and Algorithms",
        "Databases",
        "Digital Libraries",
        "Discrete Mathematics",
        "Distributed, Parallel, and Cluster Computing",
        "Emerging Technologies",
        "Formal Languages and Automata Theory",
        "General Literature",
        "Graphics",
        "Hardware Architecture",
        "Human-Computer Interaction",
        "Information Retrieval",
        "Information Theory",
        "Logic in Computer Science",
        "Machine Learning",
        "Mathematical Software",
        "Multiagent Systems",
        "Multimedia",
        "Networking and Internet Architecture",
        "Neural and Evolutionary Computing",
        "Numerical Analysis",
        "Operating Systems",
        "Other Computer Science",
        "Performance",
        "Programming Languages",
        "Robotics",
        "Social and Information Networks",
        "Software Engineering",
        "Sound",
        "Symbolic Computation",
        "Systems and Control",
    ],
    "Quantitative Biology": [
        "Biomolecules",
        "Cell Behavior",
        "Genomics",
        "Molecular Networks",
        "Neurons and Cognition",
        "Other Quantitative Biology",
        "Populations and Evolution",
        "Quantitative Methods",
        "Subcellular Processes",
        "Tissues and Organs",
    ],
    "Quantitative Finance": [
        "Computational Finance",
        "Economics",
        "General Finance",
        "Mathematical Finance",
        "Portfolio Management",
        "Pricing of Securities",
        "Risk Management",
        "Statistical Finance",
        "Trading and Market Microstructure",
    ],
    "Statistics": [
        "Applications",
        "Computation",
        "Machine Learning",
        "Methodology",
        "Other Statistics",
        "Statistics Theory",
    ],
    "Electrical Engineering and Systems Science": [
        "Audio and Speech Processing",
        "Image and Video Processing",
        "Signal Processing",
        "Systems and Control",
    ],
    "Economics": ["Econometrics", "General Economics", "Theoretical Economics"],
}


def get_topic_abbreviations_for_categories(categories):
    """
    カテゴリリストから必要なトピックのabbreviation（略称）リストを取得
    
    Args:
        categories: カテゴリ名のリスト
    
    Returns:
        dict: {abbreviation: topic_name} の辞書
        例: {"cs": "Computer Science", "eess": "Electrical Engineering and Systems Science"}
    """
    abbreviations = {}
    
    for category in categories:
        # category_mapから該当するトピックを検索
        for topic_name, topic_categories in category_map.items():
            if category in topic_categories:
                # トピック名からabbreviationを取得
                if topic_name in topics:
                    abbr = topics[topic_name]
                elif topic_name in physics_topics:
                    abbr = physics_topics[topic_name]
                else:
                    raise RuntimeError(f"Unknown topic: {topic_name}")
                
                if abbr:  # 空文字列でない場合のみ追加
                    abbreviations[abbr] = topic_name
    
    if not abbreviations:
        raise RuntimeError(f"No valid topics found for categories: {categories}")
    
    return abbreviations


def distribute_papers_by_category(papers, categories, max_total=300):
    """
    カテゴリ毎に論文を均等配分する
    
    Args:
        papers: 全論文リスト
        categories: 対象カテゴリリスト
        max_total: LLMにかける最大論文数
    
    Returns:
        配分後の論文リスト
    """
    # カテゴリ毎に論文を分類
    papers_by_category = {cat: [] for cat in categories}
    
    for paper in papers:
        processed_subjects = process_subject_fields(paper["subjects"])
        for cat in categories:
            if cat in processed_subjects:
                papers_by_category[cat].append(paper)
                break  # 最初にマッチしたカテゴリに割り当て
    
    # 各カテゴリの論文数を表示
    print(f"\n=== Category Distribution (Before Balancing) ===")
    for cat, cat_papers in papers_by_category.items():
        print(f"  {cat}: {len(cat_papers)} papers")
    
    # カテゴリ毎の最大数を計算
    max_per_category = max_total // len(categories)
    print(f"\n=== Balancing Strategy ===")
    print(f"Max total papers: {max_total}")
    print(f"Number of categories: {len(categories)}")
    print(f"Max papers per category: {max_per_category}")
    
    # 各カテゴリから関連性スコア順に最大数まで抽出
    balanced_papers = []
    for cat, cat_papers in papers_by_category.items():
        # 関連性スコアでソート（スコアがある場合のみ）
        if cat_papers and 'Relevancy score' in cat_papers[0]:
            # スコアを数値に変換してソート（降順）
            cat_papers_sorted = sorted(
                cat_papers, 
                key=lambda x: float(x.get('Relevancy score', 0)) if isinstance(x.get('Relevancy score'), (int, float, str)) else 0,
                reverse=True
            )
        else:
            cat_papers_sorted = cat_papers
        
        selected = cat_papers_sorted[:max_per_category]
        balanced_papers.extend(selected)
        
        # 選択された論文のスコアを表示
        if selected and 'Relevancy score' in selected[0]:
            scores = [x.get('Relevancy score', 'N/A') for x in selected]
            print(f"  {cat}: selected {len(selected)}/{len(cat_papers)} papers (scores: {scores})")
        else:
            print(f"  {cat}: selected {len(selected)}/{len(cat_papers)} papers")
    
    print(f"\nTotal papers after balancing: {len(balanced_papers)}")
    return balanced_papers


def generate_body(categories, interest, threshold, max_papers=300, evaluation_model="gpt-4o-mini", summary_model="gpt-3.5-turbo"):
    """
    カテゴリリストに基づいて論文を取得し、LLM評価を実行
    
    Args:
        categories: カテゴリ名のリスト（複数のトピックにまたがってもOK）
        interest: LLM評価用の興味対象記述
        threshold: 重要度スコアの閾値
        max_papers: LLM評価にかける最大論文数
        evaluation_model: LLM評価に使用するモデル名
        summary_model: 要約生成に使用するモデル名
    
    Returns:
        body: HTML形式の論文リスト
        papers: 論文のリスト（評価済みまたは未評価）
        hallucination: 幻覚検出フラグ
    """
    from download_new_papers import get_papers_from_multiple_topics
    
    if categories:
        # カテゴリから必要なトピックのabbreviationを取得
        topic_abbreviations = get_topic_abbreviations_for_categories(categories)
        print(f"\n=== Topic Detection ===")
        print(f"Required topics for categories {categories}:")
        for abbr, topic_name in topic_abbreviations.items():
            print(f"  - {topic_name} ({abbr})")
        
        # 複数トピックから論文を取得
        papers = get_papers_from_multiple_topics(topic_abbreviations)
        print(f"\n=== Paper Acquisition Results ===")
        print(f"Total papers: {len(papers)}")
        
        # Log category information for first 5 papers
        print(f"\nCategory info for first 5 papers:")
        for i, paper in enumerate(papers[:5]):
            print(f"\nPaper {i+1}:")
            print(f"  Title: {paper['title'][:80]}...")
            print(f"  Raw subjects: {paper['subjects']}")
            processed = process_subject_fields(paper['subjects'])
            print(f"  Processed: {processed}")
            matches = set(processed) & set(categories)
            print(f"  Matches: {matches if matches else 'None'}")
        
        print(f"\nFilter criteria: {categories}")
        papers = [
            t
            for t in papers
            if bool(set(process_subject_fields(t["subjects"])) & set(categories))
        ]
        print(f"Papers after filtering: {len(papers)}")
    else:
        # カテゴリ指定なしの場合はエラー
        raise RuntimeError("Categories must be specified")
    
    if interest:
        # LLM評価を実行（フィルタ後の全論文を評価）
        print(f"\n=== LLM Evaluation ===")
        print(f"Using evaluation model: {evaluation_model}")
        print(f"Evaluating {len(papers)} papers...")
        relevancy, hallucination = generate_relevance_score(
            papers,
            query={"interest": interest},
            threshold_score=threshold,
            num_paper_in_prompt=16,
            model_name=evaluation_model,
        )
        
        # デバッグ情報
        print(f"\n[DEBUG] generate_relevance_score completed")
        print(f"[DEBUG] relevancy type: {type(relevancy)}")
        print(f"[DEBUG] relevancy length: {len(relevancy) if relevancy else 0}")
        print(f"[DEBUG] hallucination: {hallucination}")
        
        # 閾値通過後にカテゴリ毎に均等配分
        if len(relevancy) > max_papers:
            print(f"\n=== Category-based Distribution (After Threshold) ===")
            relevancy = distribute_papers_by_category(relevancy, categories, max_total=max_papers)
        
        # 閾値以上の論文に要約を生成
        print(f"\n=== Summarization ===")
        print(f"Generating summaries for {len(relevancy)} important papers (score >= {threshold})...")
        print(f"Using summary model: {summary_model}")
        from summarizer import generate_summaries_batch
        relevancy = generate_summaries_batch(relevancy, model_name=summary_model)
        print(f"[DEBUG] Summarization completed for {len(relevancy)} papers")
        
        body = "<br><br>".join(
            [
                f'Title: <a href="{paper["main_page"]}">{paper["title"]}</a><br>Authors: {paper["authors"]}<br>Score: {paper["Relevancy score"]}<br>Reason: {paper["Reasons for match"]}'
                for paper in relevancy
            ]
        )
        if hallucination:
            body = (
                "Warning: the model hallucinated some papers. We have tried to remove them, but the scores may not be accurate.<br><br>"
                + body
            )
    else:
        body = "<br><br>".join(
            [
                f'Title: <a href="{paper["main_page"]}">{paper["title"]}</a><br>Authors: {paper["authors"]}'
                for paper in papers
            ]
        )
        relevancy = None
        hallucination = False
    return body, papers if not interest else relevancy, hallucination


if __name__ == "__main__":
    # Load the .env file.
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", help="yaml config file to use", default="config.yaml"
    )
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("No openai api key found")
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    categories = config["categories"]
    from_email = os.environ.get("FROM_EMAIL")
    to_email = os.environ.get("TO_EMAIL")
    threshold = config["threshold"]
    interest = config["interest"]
    max_papers = config.get("max_papers", 300)  # デフォルトは300
    evaluation_model = config.get("evaluation_model", "gpt-4o-mini")  # デフォルトはgpt-4o-mini
    summary_model = config.get("summary_model", "gpt-3.5-turbo")  # デフォルトはgpt-3.5-turbo
    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    
    try:
        print(f"\n[DEBUG] Starting generate_body...")
        body, papers, hallucination = generate_body(categories, interest, threshold, max_papers, evaluation_model, summary_model)
        print(f"[DEBUG] generate_body completed")
        print(f"[DEBUG] papers type: {type(papers)}")
        print(f"[DEBUG] papers length: {len(papers) if papers else 0}")
        
        with open("digest.html", "w", encoding="utf-8") as f:
            f.write(body)
        print("Generated digest.html")
        
        # Discord通知（要約は既に生成済み）
        if discord_webhook and papers:
            print("\nPosting to Discord...")
            # トピック名を自動検出
            topic_abbreviations = get_topic_abbreviations_for_categories(categories)
            topic_names = list(topic_abbreviations.values())
            topic_display = ", ".join(topic_names) if len(topic_names) > 1 else topic_names[0]
            
            send_to_discord(
                webhook_url=discord_webhook,
                papers_html=body,
                topic=topic_display,
                categories=categories if categories else ["All"],
                threshold=threshold,
                papers_with_summary=papers if interest else None
            )
        elif discord_webhook:
            print("\nNo papers found. Skipping Discord notification.")
        else:
            print("\nNo Discord webhook URL found. Skipping Discord notification.")
        
        # Email notification
        print(f"\n[DEBUG] Email check - SENDGRID_API_KEY: {bool(os.environ.get('SENDGRID_API_KEY'))}, from_email: {from_email}, to_email: {to_email}")
        if os.environ.get("SENDGRID_API_KEY") and from_email and to_email:
            try:
                sg = SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
                from_email_obj = Email(from_email)  # Change to your verified sender
                to_email_obj = To(to_email)
                subject = date.today().strftime("Personalized arXiv Digest, %d %b %Y")
                content = Content("text/html", body)
                mail = Mail(from_email_obj, to_email_obj, subject, content)
                mail_json = mail.get()

                # Send an HTTP POST request to /mail/send
                response = sg.client.mail.send.post(request_body=mail_json)
                if response.status_code >= 200 and response.status_code <= 300:
                    print("Send email: Success!")
                else:
                    print(f"Send email: Failure ({response.status_code}, {response.text})")
            except Exception as email_error:
                print(f"Email sending failed: {email_error}")
        else:
            print("No SendGrid API key or email address configured. Skipping email.")
    
    except Exception as e:
        import traceback
        error_msg = f"Error occurred: {str(e)}"
        print(error_msg)
        print("\n[DEBUG] Full traceback:")
        traceback.print_exc()
        if discord_webhook:
            send_error_to_discord(discord_webhook, error_msg)
        raise
