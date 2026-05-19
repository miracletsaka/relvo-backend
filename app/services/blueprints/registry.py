from . import cta
from . import features
from . import footer
from . import headline
from . import hero_media
from . import hero_text
from . import offer
from . import price
from . import product_card
from . import review
from . import sponsor


BLUEPRINTS = {
    "hero_text": hero_text,
    "hero_media": hero_media,

    "cta_button": cta,
    "feature_list": features,
    "footer": footer,
    "headline": headline,
    "offer_block": offer,
    "price_block": price,
    "product_card": product_card,
    "review_block": review,
    "sponsor_bar": sponsor,
}


def get_blueprint(segment_type: str, **kwargs):
    module = BLUEPRINTS.get(segment_type)

    if not module:
        raise ValueError(
            f"No blueprint module registered for segment_type={segment_type}"
        )

    return module.get(**kwargs)


def list_blueprint_types():
    return sorted(BLUEPRINTS.keys())