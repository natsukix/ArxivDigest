import gradio as gr
from download_new_papers import get_papers
import utils
from relevancy import generate_relevance_score, process_subject_fields
from sendgrid.helpers.mail import Mail, Email, To, Content
import sendgrid
import os
import openai

topics = {
    "Physics": "",
    "Mathematics": "math",
    "Computer Science": "cs",
    "Quantitative Biology": "q-bio",
    "Quantitative Finance": "q-fin",
    "Statistics": "stat",
    "Electrical Engineering and Systems Science": "eess",
    "Economics": "econ"
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
    "Quantum Physics": "quant-ph"
}

categories_map = {
    "Astrophysics": ["Astrophysics of Galaxies", "Cosmology and Nongalactic Astrophysics", "Earth and Planetary Astrophysics", "High Energy Astrophysical Phenomena", "Instrumentation and Methods for Astrophysics", "Solar and Stellar Astrophysics"],
    "Condensed Matter": ["Disordered Systems and Neural Networks", "Materials Science", "Mesoscale and Nanoscale Physics", "Other Condensed Matter", "Quantum Gases", "Soft Condensed Matter", "Statistical Mechanics", "Strongly Correlated Electrons", "Superconductivity"],
    "General Relativity and Quantum Cosmology": ["None"],
    "High Energy Physics - Experiment": ["None"],
    "High Energy Physics - Lattice": ["None"],
    "High Energy Physics - Phenomenology": ["None"],
    "High Energy Physics - Theory": ["None"],
    "Mathematical Physics": ["None"],
    "Nonlinear Sciences": ["Adaptation and Self-Organizing Systems", "Cellular Automata and Lattice Gases", "Chaotic Dynamics", "Exactly Solvable and Integrable Systems", "Pattern Formation and Solitons"],
    "Nuclear Experiment": ["None"],
    "Nuclear Theory": ["None"],
    "Physics": ["Accelerator Physics", "Applied Physics", "Atmospheric and Oceanic Physics", "Atomic and Molecular Clusters", "Atomic Physics", "Biological Physics", "Chemical Physics", "Classical Physics", "Computational Physics", "Data Analysis, Statistics and Probability", "Fluid Dynamics", "General Physics", "Geophysics", "History and Philosophy of Physics", "Instrumentation and Detectors", "Medical Physics", "Optics", "Physics and Society", "Physics Education", "Plasma Physics", "Popular Physics", "Space Physics"],
    "Quantum Physics": ["None"],
    "Mathematics": ["Algebraic Geometry", "Algebraic Topology", "Analysis of PDEs", "Category Theory", "Classical Analysis and ODEs", "Combinatorics", "Commutative Algebra", "Complex Variables", "Differential Geometry", "Dynamical Systems", "Functional Analysis", "General Mathematics", "General Topology", "Geometric Topology", "Group Theory", "History and Overview", "Information Theory", "K-Theory and Homology", "Logic", "Mathematical Physics", "Metric Geometry", "Number Theory", "Numerical Analysis", "Operator Algebras", "Optimization and Control", "Probability", "Quantum Algebra", "Representation Theory", "Rings and Algebras", "Spectral Theory", "Statistics Theory", "Symplectic Geometry"],
    "Computer Science": ["Artificial Intelligence", "Computation and Language", "Computational Complexity", "Computational Engineering, Finance, and Science", "Computational Geometry", "Computer Science and Game Theory", "Computer Vision and Pattern Recognition", "Computers and Society", "Cryptography and Security", "Data Structures and Algorithms", "Databases", "Digital Libraries", "Discrete Mathematics", "Distributed, Parallel, and Cluster Computing", "Emerging Technologies", "Formal Languages and Automata Theory", "General Literature", "Graphics", "Hardware Architecture", "Human-Computer Interaction", "Information Retrieval", "Information Theory", "Logic in Computer Science", "Machine Learning", "Mathematical Software", "Multiagent Systems", "Multimedia", "Networking and Internet Architecture", "Neural and Evolutionary Computing", "Numerical Analysis", "Operating Systems", "Other Computer Science", "Performance", "Programming Languages", "Robotics", "Social and Information Networks", "Software Engineering", "Sound", "Symbolic Computation", "Systems and Control"],
    "Quantitative Biology": ["Biomolecules", "Cell Behavior", "Genomics", "Molecular Networks", "Neurons and Cognition", "Other Quantitative Biology", "Populations and Evolution", "Quantitative Methods", "Subcellular Processes", "Tissues and Organs"],
    "Quantitative Finance": ["Computational Finance", "Economics", "General Finance", "Mathematical Finance", "Portfolio Management", "Pricing of Securities", "Risk Management", "Statistical Finance", "Trading and Market Microstructure"],
    "Statistics": ["Applications", "Computation", "Machine Learning", "Methodology", "Other Statistics", "Statistics Theory"],
    "Electrical Engineering and Systems Science": ["Audio and Speech Processing", "Image and Video Processing", "Signal Processing", "Systems and Control"],
    "Economics": ["Econometrics", "General Economics", "Theoretical Economics"]
}


def sample(email, topic, physics_topic, categories, interest):
    if not topic:
        raise gr.Error("トピックを選択してください。")
    if topic == "Physics":
        if isinstance(physics_topic, list):
            raise gr.Error("物理学のトピックを選択してください。")
        topic = physics_topic
        abbr = physics_topics[topic]
    else:
        abbr = topics[topic]
    if categories:
        papers = get_papers(abbr)
        papers = [
            t for t in papers
            if bool(set(process_subject_fields(t['subjects'])) & set(categories))][:4]
    else:
        papers = get_papers(abbr, limit=4)
    if interest:
        if not openai.api_key: raise gr.Error("まず左側でOpenAI APIキーを設定してください")
        relevancy, _ = generate_relevance_score(
            papers,
            query={"interest": interest},
            threshold_score=0,
            num_paper_in_prompt=4)
        return "\n\n".join([paper["summarized_text"] for paper in relevancy])
    else:
        return "\n\n".join(f"タイトル: {paper['title']}\n著者: {paper['authors']}" for paper in papers)


def change_subsubject(subject, physics_subject):
    if subject != "Physics":
        return gr.Dropdown.update(choices=categories_map[subject], value=[], visible=True)
    else:
        if physics_subject and not isinstance(physics_subject, list):
            return gr.Dropdown.update(choices=categories_map[physics_subject], value=[], visible=True)
        else:
            return gr.Dropdown.update(choices=[], value=[], visible=False)


def change_physics(subject):
    if subject != "Physics":
        return gr.Dropdown.update(visible=False, value=[])
    else:
        return gr.Dropdown.update(physics_topics, visible=True)


def test(email, topic, physics_topic, categories, interest, key):
    if not email: raise gr.Error("メールアドレスを設定してください")
    if not key: raise gr.Error("SendGridキーを設定してください")
    if topic == "Physics":
        if isinstance(physics_topic, list):
            raise gr.Error("物理学のトピックを選択してください。")
        topic = physics_topic
        abbr = physics_topics[topic]
    else:
        abbr = topics[topic]
    if categories:
        papers = get_papers(abbr)
        papers = [
            t for t in papers
            if bool(set(process_subject_fields(t['subjects'])) & set(categories))][:4]
    else:
        papers = get_papers(abbr, limit=4)
    if interest:
        if not openai.api_key: raise gr.Error("まず左側でOpenAI APIキーを設定してください")
        relevancy, hallucination = generate_relevance_score(
            papers,
            query={"interest": interest},
            threshold_score=7,
            num_paper_in_prompt=8)
        body = "<br><br>".join([f'タイトル: <a href="{paper["main_page"]}">{paper["title"]}</a><br>著者: {paper["authors"]}<br>スコア: {paper["Relevancy score"]}<br>理由: {paper["Reasons for match"]}' for paper in relevancy])
        if hallucination:
            body = "警告: モデルが存在しない論文を生成した可能性があります。削除を試みましたが、スコアが正確でない可能性があります。<br><br>" + body
    else:
        body = "<br><br>".join([f'タイトル: <a href="{paper["main_page"]}">{paper["title"]}</a><br>著者: {paper["authors"]}' for paper in papers])
    sg = sendgrid.SendGridAPIClient(api_key=key)
    from_email = Email(email)
    to_email = To(email)
    subject = "arXivダイジェスト"
    content = Content("text/html", body)
    mail = Mail(from_email, to_email, subject, content)
    mail_json = mail.get()

    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)
    if response.status_code >= 200 and response.status_code <= 300:
        return "成功!"
    else:
        return f"失敗: ({response.status_code})"


def register_openai_token(token):
    openai.api_key = token

with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column(scale=1):
            token = gr.Textbox(label="OpenAI APIキー", type="password")
            subject = gr.Radio(
                list(topics.keys()), label="トピック"
            )
            physics_subject = gr.Dropdown(physics_topics, value=[], multiselect=False, label="物理学カテゴリ", visible=False, info="")
            subsubject = gr.Dropdown(
                    [], value=[], multiselect=True, label="サブトピック", info="オプション。空欄の場合はすべてのサブトピックを使用します。", visible=False)
            subject.change(fn=change_physics, inputs=[subject], outputs=physics_subject)
            subject.change(fn=change_subsubject, inputs=[subject, physics_subject], outputs=subsubject)
            physics_subject.change(fn=change_subsubject, inputs=[subject, physics_subject], outputs=subsubject)

            interest = gr.Textbox(label="あなたの研究関心を自然言語で記述してください。この記述に基づいて選択したトピックの論文に関連性スコア（1-10）と説明を生成します。", info="Shift+Enterキーを押すか、下のボタンをクリックして更新してください。", lines=7)
            sample_btn = gr.Button("ダイジェストを生成")
            sample_output = gr.Textbox(label="設定に基づく結果。", info="実行時間の都合上、選択したトピックの最近の論文の一部のみで実行されます。論文は関連性でフィルタリングされず、1-10のスケールでソートされるだけです。")
        with gr.Column(scale=0.40):
            with gr.Box():
                title = gr.Markdown(
                    """
                    # メール設定（オプション）
                    右側の設定を使用して、以下のアドレスにメールを送信します。SendGridトークンが必要です。このページの右側を使用するだけであれば、これらの値は不要です。

                    スケジュールジョブを作成するには、[GitHubリポジトリ](https://github.com/AutoLLM/ArxivDigest)を参照してください。
                    """,
                    interactive=False, show_label=False)
                email = gr.Textbox(label="メールアドレス", type="email", placeholder="")
                sendgrid_token = gr.Textbox(label="SendGrid APIキー", type="password")
                with gr.Row():
                    test_btn = gr.Button("メール送信")
                    output = gr.Textbox(show_label=False, placeholder="メール送信状況")
    test_btn.click(fn=test, inputs=[email, subject, physics_subject, subsubject, interest, sendgrid_token], outputs=output)
    token.change(fn=register_openai_token, inputs=[token])
    sample_btn.click(fn=sample, inputs=[email, subject, physics_subject, subsubject, interest], outputs=sample_output)
    subject.change(fn=sample, inputs=[email, subject, physics_subject, subsubject, interest], outputs=sample_output)
    physics_subject.change(fn=sample, inputs=[email, subject, physics_subject, subsubject, interest], outputs=sample_output)
    subsubject.change(fn=sample, inputs=[email, subject, physics_subject, subsubject, interest], outputs=sample_output)
    interest.submit(fn=sample, inputs=[email, subject, physics_subject, subsubject, interest], outputs=sample_output)

demo.launch(show_api=False)
