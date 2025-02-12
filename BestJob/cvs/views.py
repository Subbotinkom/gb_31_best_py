from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404

# Create your views here.
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse, resolve
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView

from approvals.models import ApprovalStatus

from cvs.forms import CVCreateForm, CVUpdateForm, CVDeleteForm, CVDistributeForm, ExperienceCreateForm, \
    EducationCreateForm, LanguagesCreateForm, ModeratorCVUpdateForm
from cvs.models import CV, Experience, CVWorkSchedule, CVEmployment, Education, LanguagesSpoken, CVMonths, \
    ConnectVacancyCv

from search.models import Category, Currency, Employments, WorkSchedules, Languages, LanguageLevels, EducationLevel
from users.models import WorkerProfile


class CVList(TemplateView):
    """view список резюме соискателя"""
    template_name = 'cv_list.html'
    list_of_cvs = CV.objects.all()

    def get(self, request, *args, **kwargs):
        super(CVList, self).get(request, *args, **kwargs)
        user_id = request.user.pk
        worker_id = WorkerProfile.objects.get(user=user_id)
        context = {
            'cvs': CV.objects.filter(worker_profile=worker_id, is_active=True),
            'worker': worker_id
        }
        return self.render_to_response(context)


class ModeratorCVList(TemplateView):
    """view просмотра вакансий модератором"""
    template_name = 'moderator_cvs_list.html'

    def get(self, request, *args, **kwargs):
        super(ModeratorCVList, self).get(request, *args, **kwargs)
        context = self.get_context_data()
        context['cvs_list'] = CV.objects.all()
        return self.render_to_response(context)


class ResponseCVList(TemplateView):
    """view список откликов на резюме соискателя"""
    template_name = 'cv_response_list.html'

    def get(self, request, *args, **kwargs):
        super(ResponseCVList, self).get(request, *args, **kwargs)
        worker_id = WorkerProfile.objects.get(user=request.user.pk)
        cv_worker_ids = [cv.id for cv in CV.objects.filter(worker_profile=worker_id, is_active=True)]

        context = {
            'responses': ConnectVacancyCv.objects.filter(cv_id__in=cv_worker_ids),
        }
        return self.render_to_response(context)


class ModeratorCVUpdate(UpdateView):
    """view изменения вакансий"""
    model = CV
    template_name = 'moderator_cvs_approve.html'
    form_class = ModeratorCVUpdateForm
    success_url = reverse_lazy('cvs:moderator_cvs_list')

    def get(self, request, *args, **kwargs):
        super(ModeratorCVUpdate, self).get(request, *args, **kwargs)
        context = self.get_context_data()
        cv_id = self.kwargs['pk']
        cv = CV.objects.get(pk=cv_id)
        cv_user_id = cv.worker_profile.user_id
        worker = WorkerProfile.objects.filter(user_id=cv_user_id)
        if worker:
            context['worker'] = worker.first()

        if cv.speciality_id:
            speciality = Category.objects.get(pk=cv.speciality_id)
            context['speciality'] = speciality

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(data=request.POST)
        cv_id = self.kwargs['pk']
        if form.is_valid():
            CV.objects.filter(pk=cv_id).update(status=form.instance.status)
        else:
            print(form.errors)
        return redirect(self.success_url)


class CVCreate(CreateView):
    """view создание резюме"""
    model = CV
    template_name = 'cv_create.html'
    form_class = CVCreateForm
    success_url = reverse_lazy('cv:cv_list')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(CVCreate, self).get_context_data(**kwargs)
        context['title'] = 'Новое резюме'
        return context

    def get(self, request, *args, **kwargs):
        super(CVCreate, self).get(request, *args, **kwargs)
        worker = WorkerProfile.objects.get(user=request.user.pk)
        context = self.get_context_data()
        context['worker'] = worker
        context['employments'] = Employments.objects.all()
        context['schedules'] = WorkSchedules.objects.all()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        worker = WorkerProfile.objects.get(user=request.user.pk)
        start_status = ApprovalStatus.objects.get(status='NPB')
        form = self.form_class(data=request.POST)
        if form.is_valid():
            # сохраняем новое резюме
            cv = form.save(commit=False)
            cv.worker_profile = worker
            cv.status = start_status
            cv.save()

            for key, value in form.data.items():
                if key.startswith('schedule_'):
                    schedule = WorkSchedules.objects.get(code=value)
                    cv_schedule = CVWorkSchedule(cv=cv, schedule=schedule)
                    cv_schedule.save()
                    print(cv_schedule.schedule)
                elif key.startswith('empl_'):
                    employment = Employments.objects.get(code=value)
                    cv_employment = CVEmployment(cv=cv, employment=employment)
                    cv_employment.save()

            #   Нажата кнопка Добавить опыт работы
            if request.POST.get('experience', None):
                return redirect('cv:create_experience', pk=cv.id)
            #   Нажата кнопка Добавить место обучения
            if request.POST.get('education', None):
                return redirect('cv:create_education', cv_id=cv.id)

            if request.POST.get('language', None):
                return redirect('cv:create_language', cv_id=cv.id)

            return redirect(self.success_url)
        else:
            print(form.errors)
        return self.form_invalid(form)


class CVUpdate(UpdateView):
    """view изменение резюме"""
    model = CV
    template_name = 'cv_update.html'
    form_class = CVUpdateForm
    success_url = reverse_lazy('cv:cv_list')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(CVUpdate, self).get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        super(CVUpdate, self).get(request, *args, **kwargs)
        context = self.get_context_data()
        cv_id = kwargs.get('pk')
        cv = CV.objects.get(id=cv_id)
        worker = WorkerProfile.objects.get(user=request.user.pk)
        context['cv_id'] = cv.id
        context['worker'] = worker
        context['speciality'] = Category.objects.all().order_by('name')
        context['experience'] = Experience.objects.filter(cv=cv)
        context['educations'] = Education.objects.filter(cv=cv)
        context['langlevels'] = LanguagesSpoken.objects.filter(cv=cv)
        cv_employments = [cv_empl.employment_id for cv_empl in CVEmployment.objects.filter(cv=cv)]
        context['cv_employments'] = cv_employments
        context['employments'] = Employments.objects.all()
        cv_schedules = [cv_sch.schedule_id for cv_sch in CVWorkSchedule.objects.filter(cv=cv)]
        context['cv_schedules'] = cv_schedules
        context['schedules'] = WorkSchedules.objects.all()
        return self.render_to_response(context)


    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(request.POST, instance=self.object)

        if form.is_valid():

            self.object.save()

            cv_schedules = CVWorkSchedule.objects.filter(cv=self.object)
            cv_schedules.delete()
            cv_employments = CVEmployment.objects.filter(cv=self.object)
            cv_employments.delete()
            for key, value in form.data.items():
                if key.startswith('schedule_'):
                    schedule = WorkSchedules.objects.get(code=value)
                    cv_schedule = CVWorkSchedule(cv=self.object, schedule=schedule)
                    cv_schedule.save()
                elif key.startswith('empl_'):
                    employment = Employments.objects.get(code=value)
                    cv_employment = CVEmployment(cv=self.object, employment=employment)
                    cv_employment.save()
            return redirect(self.success_url)
        else:
            print(form.errors)
        return self.form_invalid(form)


class CVDelete(DeleteView):
    """view удаление резюме"""
    model = CV
    template_name = 'cv_delete.html'
    form_class = CVDeleteForm
    success_url = reverse_lazy('cv:cv_list')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(CVDelete, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


# class CVDistribute(TemplateView):
#     """view для размещения резюме"""
#     model = CV
#     # template_name = 'cv_distribute.html'
#     # form_class = CVDistributeForm
#     success_url = reverse_lazy('cv:cv_list')
#
#     # def get_context_data(self, *, object_list=None, **kwargs):
#     #     context = super(CVDistribute, self).get_context_data(**kwargs)
#     #     return context
#
#     def get(self, request, *args, **kwargs):
#         return self.post(request, *args, **kwargs)

def set_public_status(request, pk):
    cv = get_object_or_404(CV, pk=pk)
    cv.status = ApprovalStatus.objects.get(status='PUB')
    cv.save()
    return HttpResponseRedirect(reverse('cv:cv_list'))

# def order_forming_complete(request, pk): # метод формирования статуса
#     order = get_object_or_404(Order, pk=pk)
#     order.status = Order.SEND_TO_PROCEED
#     order.save()
#     return HttpResponseRedirect(reverse('orders:list'))


class CVExperienceCreate(CreateView):
    """Создание опыта работы"""
    model = Experience
    template_name = 'cv_experience.html'
    form_class = ExperienceCreateForm


    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Место работы'
        context['months'] = CVMonths
        context['cv_id'] = self.kwargs['pk']
        return context

    def get(self, request, *args, **kwargs):
        super(CVExperienceCreate, self).get(request, *args, **kwargs)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        cv = CV.objects.get(id=self.kwargs.get('pk'))
        form = self.form_class(data=request.POST)
        if form.is_valid():
            # сохраняем новый так сказать опыт)
            experience = form.save(commit=False)
            experience.cv = cv
            experience.save()
            return redirect('cv:update_cv', pk=cv.id)
        else:
            messages.error(request, form.errors)
            print(form.errors)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVExperienceUpdate(UpdateView):
    """Изменение опыта работы"""
    model = Experience
    template_name = 'cv_experience.html'
    form_class = ExperienceCreateForm
    success_url = reverse_lazy('cv:cv_list' )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Место работы'
        context['months'] = CVMonths
        exp = Experience.objects.get(id=self.kwargs.get('pk'))
        context['cv_id'] = exp.cv.id
        return context

    def get(self, request, *args, **kwargs):
        super(CVExperienceUpdate, self).get(request, *args, **kwargs)
        context = self.get_context_data()
        # exp = Experience.objects.get(id=self.kwargs.get('pk'))
        # context['cv_id'] = exp.cv.id
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        super(CVExperienceUpdate, self).post(request, *args, **kwargs)
        self.object = self.get_object()
        form = self.form_class(data=request.POST)
        if form.is_valid():
            return redirect('cv:update_cv', pk=self.object.cv.id)
        else:
            messages.error(request, form.errors)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVExperienceDelete(DeleteView):
    """Удаление опыта работы без поднятия формы"""
    model = Experience

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVEducationCreate(CreateView):
    """Создание места обучения"""
    model = Education
    template_name = 'cv_education.html'
    form_class = EducationCreateForm

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Место работы'
        context['cv_id'] = self.kwargs['cv_id']
        return context

    def post(self, request, *args, **kwargs):
        cv = CV.objects.get(id=self.kwargs.get('cv_id'))
        form = self.form_class(data=request.POST)
        if form.is_valid():
            # сохраняем новое место обучения
            education = form.save(commit=False)
            education.cv = cv
            education.save()
            return redirect('cv:update_cv', pk=cv.id)
        else:
            messages.error(request, form.errors)
            print(form.errors)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVEducationUpdate(UpdateView):
    """Редактирование места обучения"""
    model = Education
    template_name = 'cv_education.html'
    form_class = EducationCreateForm
    success_url = reverse_lazy('cv:cv_list')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Место обучения'
        educ = Education.objects.get(id=self.kwargs.get('pk'))
        context['cv_id'] = educ.cv.id
        return context

    def post(self, request, *args, **kwargs):
        super(CVEducationUpdate, self).post(request, *args, **kwargs)
        self.object = self.get_object()
        form = self.form_class(data=request.POST)
        if form.is_valid():
            return redirect('cv:update_cv', pk=self.object.cv.id)
        else:
            messages.error(request, form.errors)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVEducationDelete(DeleteView):
    """Удаление места обучения без поднятия формы"""
    model = Education

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVLanguageCreate(CreateView):
    """Создание вледения языком"""
    model = LanguagesSpoken
    template_name = 'cv_languages.html'
    form_class = LanguagesCreateForm
    success_url = reverse_lazy('cv:cv_list')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Владение языком'
        context['cv_id'] = self.kwargs['cv_id']
        return context

    def post(self, request, *args, **kwargs):
        cv = CV.objects.get(id=self.kwargs.get('cv_id'))
        form = self.form_class(data=request.POST)
        if form.is_valid():
            # сохраняем новый язык
            language = form.save(commit=False)
            language.cv = cv
            language.save()
            return redirect('cv:update_cv', pk=cv.id)
        else:
            messages.error(request, form.errors)
            print(form.errors)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class CVLanguageUpdate(UpdateView):
    """Изменение вледения языком"""
    model = LanguagesSpoken
    template_name = 'cv_languages.html'
    form_class = LanguagesCreateForm
    success_url = reverse_lazy('cv:cv_list')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Владение языком'
        lang = LanguagesSpoken.objects.get(id=self.kwargs.get('pk'))
        context['cv_id'] = lang.cv.id
        return context

    def post(self, request, *args, **kwargs):
        super(CVLanguageUpdate, self).post(request, *args, **kwargs)
        self.object = self.get_object()
        form = self.form_class(data=request.POST)
        if form.is_valid():
            return redirect('cv:update_cv', pk=self.object.cv.id)
        else:
            messages.error(request, form.errors)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

class CVLanguageDelete(DeleteView):
    """Удаление вледения языком без формы"""
    model = LanguagesSpoken

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))