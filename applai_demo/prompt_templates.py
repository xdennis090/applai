TEMPLATE_FORMAL = """
Sehr geehrte Damen und Herren,
über die von Ihnen veröffentlichte Stellenanzeige habe ich mich sehr gefreut, da Ihre Anforderungen an die ausgeschriebene Stelle und meine Person hervorragend zueinanderpassen. Deshalb freue ich mich darüber, mich heute bei Ihnen bewerben zu dürfen.
Seit meinem Abschluss bin ich in diesem Bereich tätig. Insbesondere umfassen meine Aufgabengebiete die Analyse, die Ermittlung von Bedarf und die Unterstützung bei komplexen Strukturen. Aufgrund der hier erworbenen Fähigkeiten und Erfahrungen bin ich in der Lage mich schnell und umfassend in das neue Aufgabengebiet einfinden zu können. Gerne bringe ich neben meinem fachlichen Wissen und meinen Erfahrungen auch meine ganz persönlichen Stärken mit in den Berufsalltag ein. Als solche empfinde ich meine Loyalität, meine Kommunikationsfähigkeit sowie mein Verantwortungsbewusstsein.
Ich würde mich freuen, wenn meine Gehaltsvorstellungen in Ihr Gefüge passen. Der nächstmögliche Einstellungstermin ist kurzfristig zu realisieren.
Für ein persönliches Gespräch stehe ich Ihnen gerne zur Verfügung und freue mich auf Ihre Einladung.
Mit freundlichen Grüßen
"""

TEMPLATE_VALUES = """
Sehr geehrte Damen und Herren,
die Ausrichtung, für die Ihr Unternehmen bekannt ist, stimmt sehr mit den Werten überein, die ich vertrete: Ein respektvolles Miteinander und hohe Qualität. Durch meine Arbeit möchte ich dazu beitragen, diese Werte weiterzuentwickeln. Deshalb bin ich überzeugt, dass ich Ihr Team sehr gut ergänze.
Nach meiner Berufserfahrung habe ich bereits unterschiedlichste Projekte begleitet. Im Zuge neuer Herausforderungen habe ich selbstständig Konzepte und Maßnahmen entwickelt. Diese wurden von der Leitung auch erfolgreich umgesetzt. Dabei habe ich festgestellt, dass mir die Vermittlung von Werten und Qualität ein besonderes Anliegen ist. Darüber hinaus habe ich an der Einführung von neuen Konzepten mitgewirkt. Diesen Bereich zu fördern, liegt mir sehr am Herzen.
Bei Ihnen kann ich mein Wissen, meine Erfahrung und meine Leidenschaft gezielt einsetzen, um unsere übereinstimmenden Ziele zu erreichen. Außerdem bin ich überzeugt, dass wir gegenseitig viel voneinander lernen können.
Ich freue mich auf die Möglichkeit, mich Ihnen persönlich vorzustellen.
Mit freundlichen Grüßen
"""

TEMPLATE_MODERN = """
Sehr geehrte Damen und Herren,
der Markt, in dem Sie aktiv sind, finde ich überaus interessant. Neben dem großen Potenzial begeistert mich vor allem auch der Nutzen Ihres Produkts. Sie verkaufen nicht einfach irgendwas, sondern lösen konkrete Probleme und bieten echten Mehrwert. Mit meiner Erfahrung und einer Leidenschaft für authentische Ergebnisse, bin ich überzeugt, Ihr Team sehr gut zu ergänzen.
Nach meinem Abschluss war ich für wichtige Kernaufgaben zuständig. Im ersten Jahr erreichte ich messbare Erfolge und verfeinerte meine Kompetenz. Im Anschluss verlagerte sich mein Schwerpunkt auf die Betreuung und den Ausbau der Prozesse. Hier konnte ich maßgeblich dazu beitragen, durch eine serviceorientierte Kommunikation langfristige Erfolge aufzubauen. Allein im letzten Jahr ist die Zufriedenheit messbar gestiegen.
Bereits in vorherigen Stationen eignete ich mir das analytische und strategische Wissen an, um Chancen zu identifizieren und zielgerichtet zu nutzen. Beispielsweise erstellte ich Analysen und leitete daraus Handlungsempfehlungen ab. Diese wurden auch erfolgreich umgesetzt.
Daher sehe ich mich auch bei Ihnen als treibende Kraft, um vielversprechende Ergebnisse für das Unternehmen zu erzielen. Ich freue mich, meine Fähigkeiten unter Beweis stellen zu dürfen und stelle mich Ihnen gerne persönlich vor.
Mit freundlichen Grüßen
"""

TEMPLATE_STUDENT = """
Sehr geehrte Damen und Herren,
an der Position bei Ihnen reizen mich vor allem die vielfältigen Entwicklungswege, die in Ihrem Unternehmen integriert sind. Denn seit Beginn meines Studiums begeistert mich dieses Thema. Den Einstieg bei Ihnen sehe ich als idealen Startpunkt, um mein Wissen aus dem Studium zu praktischer Erfahrung und Kompetenz auszubauen.
In meinem Studium habe ich den Schwerpunkt passend gewählt. Dabei habe ich gezielt Seminare zu den relevanten Themen besucht. In Teamarbeit habe ich Strategien und Pläne erstellt und bin auch mit praktischen Aspekten in Berührung gekommen. Außerdem habe ich gelernt, Analysen und Bewertungen durchzuführen. Von meinen Professoren werde ich aufgrund meines reflektierten und eigenständigen Vorgehens sowie meiner strukturierten Arbeitsweise geschätzt.
Mein Ziel ist es, mit meinem Engagement und durch intensive praktische Erfahrungen zu einem Experten in diesem Bereich zu werden. Deshalb möchte ich mich tatkräftig bei Ihnen einbringen und dazu beitragen, die Prozesse noch besser und effektiver zu gestalten.
Habe ich Ihr Interesse geweckt? Dann freue ich mich darauf, mich Ihnen persönlich vorzustellen.
Mit freundlichen Grüßen
"""

def get_template_by_tone(tone):
    t = tone.lower()
    if t == 'locker':
        return TEMPLATE_MODERN
    elif t == 'kreativ':
        return TEMPLATE_VALUES
    elif t == 'neutral':
        return TEMPLATE_STUDENT
    else:
        return TEMPLATE_FORMAL