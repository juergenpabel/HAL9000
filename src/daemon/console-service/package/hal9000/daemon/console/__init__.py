from flet_routed_app import MvpViewBuilder


class CounterModel:
	pass
class CounterPresenter:
	pass
class CounterView:
	pass


@route("/main")
class MainViewBuilder(MvpViewBuilder):
    data_source_class = CounterModel
    view_class = CounterView
    presenter_class = CounterPresenter

